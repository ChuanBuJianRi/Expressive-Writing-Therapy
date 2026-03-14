"""Story API routes — the main story generation pipeline."""
import json
import uuid
from flask import Blueprint, request, jsonify, Response, stream_with_context
from app.services.world_builder import build_world
from app.services.chapter_planner import plan_chapters
from app.services.director_agent import direct_chapter
from app.services.character_agent import generate_character_action
from app.services.story_composer import compose_chapter
from app.services.safety_filter import check_safety
from app.services.preset_manager import get_world_by_id, get_character_by_id
from app.api.session import save_session
from app.models.story import Story, Chapter
from app.models.character import Character
from app.utils.logger import get_logger

log = get_logger(__name__)

story_bp = Blueprint("story", __name__)

# In-memory story store
_stories: dict[str, Story] = {}


def _resolve_characters(char_data_list: list[dict]) -> list[dict]:
    """Resolve characters from preset IDs or inline definitions."""
    characters = []
    for cd in char_data_list:
        preset_id = cd.get("preset_id")
        if preset_id:
            preset = get_character_by_id(preset_id)
            if preset:
                characters.append(preset)
                continue
        characters.append(cd)
    return characters


def _sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@story_bp.route("/start", methods=["POST"])
def start_story():
    """Initialize a story session.

    Request body:
    {
        "theme": "孤独与连接",
        "tags": ["治愈", "现实"],
        "characters": [{"name": "...", "personality": "..."}, ...],
        "world_preset_id": "enchanted_forest" (optional),
        "custom_setting": "" (optional),
        "num_chapters": 3
    }
    """
    data = request.get_json() or {}
    theme = data.get("theme", "")
    if not theme:
        return jsonify({"error": "theme is required"}), 400

    session_id = str(uuid.uuid4())[:12]
    tags = data.get("tags", [])
    num_chapters = min(data.get("num_chapters", 3), 10)
    characters_input = data.get("characters", [])

    # Resolve characters
    characters = _resolve_characters(characters_input)
    if not characters:
        # Use 2 default characters if none provided
        characters = [
            get_character_by_id("healer"),
            get_character_by_id("seeker"),
        ]

    # Resolve world
    world_preset_id = data.get("world_preset_id")
    if world_preset_id:
        world_config = get_world_by_id(world_preset_id)
        if not world_config:
            world_config = build_world(theme, tags=tags)
    else:
        custom_setting = data.get("custom_setting", "")
        world_config = build_world(theme, tags=tags, custom_setting=custom_setting)

    # Plan chapters
    chapter_plans = plan_chapters(
        world_config=world_config.get("setting", world_config),
        characters=characters,
        num_chapters=num_chapters,
        theme=theme,
    )

    # Create story
    story = Story(
        session_id=session_id,
        theme=theme,
        world_config=world_config,
        chapter_plans=chapter_plans,
        status="initialized",
    )
    _stories[session_id] = story

    # Save session
    save_session(session_id, {
        "id": session_id,
        "theme": theme,
        "characters": characters,
        "world_config": world_config,
        "num_chapters": num_chapters,
        "status": "initialized",
    })

    return jsonify({
        "session_id": session_id,
        "world": world_config,
        "chapter_plans": [p.to_dict() for p in chapter_plans],
        "characters": characters,
        "status": "initialized",
    })


@story_bp.route("/generate-chapter", methods=["POST"])
def generate_chapter():
    """Generate the next chapter using the multi-agent pipeline.

    Supports SSE streaming for real-time progress updates.

    Request body:
    {
        "session_id": "abc123",
        "user_input": "" (optional — user intervention/guidance)
    }
    """
    data = request.get_json() or {}
    session_id = data.get("session_id", "")
    user_input = data.get("user_input", "")

    story = _stories.get(session_id)
    if not story:
        return jsonify({"error": "Session not found. Call /api/story/start first."}), 404

    from app.api.session import get_session
    session = get_session(session_id)
    characters = session.get("characters", []) if session else []

    chapter_index = len(story.chapters)
    if chapter_index >= len(story.chapter_plans):
        return jsonify({"error": "All chapters have been generated.", "status": "completed"})

    plan = story.chapter_plans[chapter_index]
    accept = request.headers.get("Accept", "")

    if "text/event-stream" in accept:
        return Response(
            stream_with_context(_generate_chapter_stream(
                story, characters, plan, chapter_index, user_input
            )),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Non-streaming: run entire pipeline and return result
    chapter = _run_chapter_pipeline(story, characters, plan, chapter_index, user_input)
    return jsonify({
        "chapter": chapter.to_dict(),
        "chapter_number": chapter_index + 1,
        "total_chapters": len(story.chapter_plans),
        "status": story.status,
    })


def _generate_chapter_stream(story, characters, plan, chapter_index, user_input):
    """Generator for SSE streaming of chapter generation."""
    yield _sse_event("progress", {"step": "director", "message": "导演正在规划剧情...", "progress": 10})

    # Step 1: Director
    previous_chapters = [c.to_dict() for c in story.chapters]
    directions = direct_chapter(
        world_config=story.world_config,
        characters=characters,
        chapter_plan=plan.to_dict(),
        previous_chapters=previous_chapters,
        user_input=user_input,
    )

    yield _sse_event("log", {
        "sender": "🎬 导演",
        "cls": "director",
        "text": directions.get("chapter_events", ""),
    })
    yield _sse_event("progress", {"step": "characters", "message": "角色们正在行动...", "progress": 30})

    # Step 2: Character agents
    char_instructions = directions.get("character_instructions", {})
    scene_setting = directions.get("scene_setting", "")
    actions = []
    public_actions = []

    for i, char in enumerate(characters):
        char_id = char.get("id", str(i))
        instruction = char_instructions.get(char_id, {
            "private_instruction": "自由发挥，展现你的角色特色。",
            "emotional_goal": "展现真实的自我。",
            "interaction_hints": "与他人交流。",
        })

        action = generate_character_action(
            character=char,
            world_config=story.world_config,
            director_instruction=instruction,
            scene_setting=scene_setting,
            other_characters_public=public_actions,
        )
        actions.append(action)
        public_actions.append({
            "name": char["name"],
            "public_action": action.public_action,
            "dialogue": action.dialogue,
        })

        # Update character memory
        char.setdefault("memory", []).append({
            "chapter": chapter_index + 1,
            "public_action": action.public_action,
            "private_thought": action.private_thought,
        })

        yield _sse_event("log", {
            "sender": f"🎭 {char['name']}",
            "cls": f"char-{char_id}",
            "text": action.dialogue if action.dialogue else action.public_action,
        })

        pct = 30 + int((i + 1) / len(characters) * 30)
        yield _sse_event("progress", {
            "step": "characters",
            "message": f"{char['name']}已行动",
            "progress": pct,
        })

    yield _sse_event("progress", {"step": "composing", "message": "正在整合叙事...", "progress": 70})

    # Step 3: Compose
    prose = compose_chapter(
        chapter_plan=plan.to_dict(),
        scene_setting=scene_setting,
        character_actions=actions,
        world_config=story.world_config,
        chapter_number=chapter_index + 1,
        therapeutic_intention=directions.get("therapeutic_intention", ""),
    )

    yield _sse_event("log", {
        "sender": "📝 叙事者",
        "cls": "composer",
        "text": "故事已整合完成",
    })
    yield _sse_event("progress", {"step": "safety", "message": "安全审查中...", "progress": 85})

    # Step 4: Safety filter
    safety_result = check_safety(prose)

    yield _sse_event("log", {
        "sender": "🛡️ 安全审查 (watsonx.ai)",
        "cls": "safety",
        "text": f"安全评分: {safety_result['safety_score']:.1f} | 治疗价值: {safety_result['therapeutic_score']:.1f}",
    })

    # Build chapter
    chapter = Chapter(
        chapter_number=chapter_index + 1,
        title=plan.title,
        prose=prose,
        character_actions=actions,
        safety_score=safety_result.get("safety_score", 1.0),
        therapeutic_notes=safety_result.get("recommendations", ""),
    )
    story.chapters.append(chapter)
    story.status = "completed" if len(story.chapters) >= len(story.chapter_plans) else "generating"

    yield _sse_event("progress", {"step": "done", "message": "生成完成！", "progress": 100})
    yield _sse_event("chapter", {
        "chapter": chapter.to_dict(),
        "chapter_number": chapter_index + 1,
        "total_chapters": len(story.chapter_plans),
        "safety": safety_result,
        "status": story.status,
    })


def _run_chapter_pipeline(story, characters, plan, chapter_index, user_input=""):
    """Run the full chapter generation pipeline (non-streaming)."""
    previous_chapters = [c.to_dict() for c in story.chapters]

    # Step 1: Director
    directions = direct_chapter(
        world_config=story.world_config,
        characters=characters,
        chapter_plan=plan.to_dict(),
        previous_chapters=previous_chapters,
        user_input=user_input,
    )

    # Step 2: Character agents
    char_instructions = directions.get("character_instructions", {})
    scene_setting = directions.get("scene_setting", "")
    actions = []
    public_actions = []

    for i, char in enumerate(characters):
        char_id = char.get("id", str(i))
        instruction = char_instructions.get(char_id, {
            "private_instruction": "自由发挥。",
            "emotional_goal": "展现真实的自我。",
            "interaction_hints": "与他人交流。",
        })

        action = generate_character_action(
            character=char,
            world_config=story.world_config,
            director_instruction=instruction,
            scene_setting=scene_setting,
            other_characters_public=public_actions,
        )
        actions.append(action)
        public_actions.append({
            "name": char["name"],
            "public_action": action.public_action,
            "dialogue": action.dialogue,
        })

        char.setdefault("memory", []).append({
            "chapter": chapter_index + 1,
            "public_action": action.public_action,
            "private_thought": action.private_thought,
        })

    # Step 3: Compose
    prose = compose_chapter(
        chapter_plan=plan.to_dict(),
        scene_setting=scene_setting,
        character_actions=actions,
        world_config=story.world_config,
        chapter_number=chapter_index + 1,
        therapeutic_intention=directions.get("therapeutic_intention", ""),
    )

    # Step 4: Safety filter
    safety_result = check_safety(prose)

    chapter = Chapter(
        chapter_number=chapter_index + 1,
        title=plan.title,
        prose=prose,
        character_actions=actions,
        safety_score=safety_result.get("safety_score", 1.0),
        therapeutic_notes=safety_result.get("recommendations", ""),
    )
    story.chapters.append(chapter)
    story.status = "completed" if len(story.chapters) >= len(story.chapter_plans) else "generating"

    return chapter


@story_bp.route("/user-input", methods=["POST"])
def user_input():
    """Allow user to interact with the Director mid-story."""
    data = request.get_json() or {}
    session_id = data.get("session_id", "")
    message = data.get("message", "")

    if not session_id or not message:
        return jsonify({"error": "session_id and message are required"}), 400

    story = _stories.get(session_id)
    if not story:
        return jsonify({"error": "Session not found"}), 404

    return jsonify({
        "status": "accepted",
        "message": "Your input will be considered in the next chapter generation.",
        "session_id": session_id,
    })


@story_bp.route("/status/<session_id>", methods=["GET"])
def get_status(session_id: str):
    """Get story generation status."""
    story = _stories.get(session_id)
    if not story:
        return jsonify({"error": "Session not found"}), 404

    return jsonify({
        "session_id": session_id,
        "status": story.status,
        "chapters_generated": len(story.chapters),
        "total_chapters": len(story.chapter_plans),
    })


@story_bp.route("/generate-choices", methods=["POST"])
def generate_choices():
    """Generate 3 branch choices for the next chapter.

    Request body: { "session_id": "...", "num_choices": 3 }
    """
    data = request.get_json() or {}
    session_id = data.get("session_id", "")
    num_choices = min(data.get("num_choices", 3), 4)

    story = _stories.get(session_id)
    if not story:
        return jsonify({"error": "Session not found"}), 404
    if not story.chapters:
        return jsonify({"error": "No chapters generated yet"}), 400

    last = story.chapters[-1]
    world_desc = story.world_config.get("description", "") or str(story.world_config)[:200]
    char_names = ", ".join(c.get("name", "") for c in _get_session_characters(session_id))

    from app.utils.llm_client import chat_json
    prompt = (
        f"Story theme: {story.theme}\n"
        f"World: {world_desc}\n"
        f"Characters: {char_names}\n\n"
        f"Last chapter excerpt:\n{last.prose[:600]}\n\n"
        f"Generate {num_choices} meaningfully distinct choices for what could happen next. "
        "Each choice should lead the story in a different emotional or narrative direction.\n"
        f'Return JSON: {{"choices": [{{"id": "A", "title": "short dramatic title (≤6 words)", '
        '"description": "2 sentences describing what happens"}}]}}'
    )
    try:
        result = chat_json([{"role": "user", "content": prompt}], temperature=0.95)
        import json as _json
        parsed = _json.loads(result)
        return jsonify(parsed)
    except Exception as e:
        log.error("generate_choices error: %s", e)
        return jsonify({"error": str(e)}), 500


def _get_session_characters(session_id: str) -> list[dict]:
    from app.api.session import get_session
    session = get_session(session_id)
    return session.get("characters", []) if session else []


@story_bp.route("/suggest", methods=["POST"])
def suggest():
    """Generate AI suggestions for story title, theme, or world keywords.

    Request body: { "type": "title"|"theme"|"keywords", "context": "..." }
    """
    data = request.get_json() or {}
    suggest_type = data.get("type", "title")
    context = data.get("context", "")

    from app.utils.llm_client import chat_json
    if suggest_type == "title":
        prompt = (
            f"Context: {context}\n"
            "Generate 5 evocative story titles (2-6 words each). "
            'Return JSON: {"suggestions": ["title1", "title2", ...]}'
        )
    elif suggest_type == "theme":
        prompt = (
            f"Context: {context}\n"
            "Generate 5 compelling story themes or central conflicts (one sentence each). "
            'Return JSON: {"suggestions": ["theme1", "theme2", ...]}'
        )
    else:  # keywords
        prompt = (
            f"Story concept: {context}\n"
            "Generate world-building keywords in 4 categories. "
            'Return JSON: {"categories": [{"name": "Environment", "words": [...]}, '
            '{"name": "Atmosphere", "words": [...]}, '
            '{"name": "Era / Tech", "words": [...]}, '
            '{"name": "Special Elements", "words": [...]}]}'
        )

    try:
        import json as _json
        result = chat_json([{"role": "user", "content": prompt}], temperature=0.9)
        return jsonify(_json.loads(result))
    except Exception as e:
        log.error("suggest error: %s", e)
        return jsonify({"error": str(e)}), 500


@story_bp.route("/export/<session_id>", methods=["GET"])
def export_story(session_id: str):
    """Export the complete story."""
    story = _stories.get(session_id)
    if not story:
        return jsonify({"error": "Session not found"}), 404

    fmt = request.args.get("format", "json")

    if fmt == "text":
        text = f"# {story.theme}\n\n"
        for ch in story.chapters:
            text += f"## 第{ch.chapter_number}章: {ch.title}\n\n"
            text += ch.prose + "\n\n"
        return Response(text, mimetype="text/plain; charset=utf-8")

    return jsonify(story.to_dict())
