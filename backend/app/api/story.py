"""Story API — scene-by-scene generation pipeline with tension-based branching."""
import json
import uuid
from flask import Blueprint, request, jsonify, Response, stream_with_context

from app.services.world_builder import build_world
from app.services.chapter_planner import plan_chapters, extend_story
from app.services.director_agent import plan_scenes, gather_all_private_states, direct_scene
from app.services.character_agent import generate_character_action
from app.services.story_composer import compose_scene
from app.services.safety_filter import check_safety
from app.services.preset_manager import get_world_by_id, get_character_by_id
from app.api.session import save_session, get_session
from app.models.story import Story, Chapter, Scene
from app.utils.logger import get_logger
from app.utils.llm_client import chat_json

log = get_logger(__name__)
story_bp = Blueprint("story", __name__)

# In-memory store
_stories: dict[str, Story] = {}

TENSION_THRESHOLD = 0.72   # scenes above this can become decision points


# ═══════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _resolve_characters(char_data_list: list[dict]) -> list[dict]:
    result = []
    for cd in char_data_list:
        if cd.get("preset_id"):
            preset = get_character_by_id(cd["preset_id"])
            if preset:
                result.append(preset)
                continue
        result.append(cd)
    return result


def _prev_prose(story: Story, max_chars: int = 800) -> str:
    """Return recent prose context from the last 2 chapters."""
    prose = ""
    for ch in story.chapters[-2:]:
        prose += f"\n--- Chapter {ch.chapter_number} ---\n{ch.prose[:max_chars // 2]}\n"
    return prose


# ═══════════════════════════════════════════════════
# /start
# ═══════════════════════════════════════════════════

@story_bp.route("/start", methods=["POST"])
def start_story():
    """Initialize a story session.

    Body: { theme, tags, characters, world_preset_id?, custom_setting?,
            num_chapters?, chapter_length_hint?, tension_threshold? }
    """
    data = request.get_json() or {}
    theme = data.get("theme", "").strip()
    if not theme:
        return jsonify({"error": "theme is required"}), 400

    session_id = str(uuid.uuid4())[:12]
    tags = data.get("tags", [])
    num_chapters = min(data.get("num_chapters", 1), 20)
    chapter_length_hint = data.get("chapter_length_hint", "medium")
    tension_threshold = float(data.get("tension_threshold", TENSION_THRESHOLD))
    characters_input = data.get("characters", [])

    core_characters = _resolve_characters(characters_input)
    if not core_characters:
        core_characters = [c for c in [get_character_by_id("healer"), get_character_by_id("seeker")] if c]

    world_preset_id = data.get("world_preset_id")
    if world_preset_id:
        world_config = get_world_by_id(world_preset_id) or build_world(theme, tags=tags)
    else:
        world_config = build_world(
            theme,
            tags=tags,
            custom_setting=data.get("custom_setting", "") +
                           ("\nDirector notes: " + data.get("user_hint", "") if data.get("user_hint") else ""),
        )

    chapter_plans = plan_chapters(
        world_config=world_config.get("setting", world_config),
        characters=core_characters,
        num_chapters=num_chapters,
        theme=theme,
        chapter_length_hint=chapter_length_hint,
    )

    story = Story(
        session_id=session_id,
        theme=theme,
        world_config=world_config,
        chapter_plans=chapter_plans,
        core_characters=core_characters,
        story_characters=[],
        status="initialized",
    )
    _stories[session_id] = story

    save_session(session_id, {
        "id": session_id,
        "theme": theme,
        "core_characters": core_characters,
        "story_characters": [],
        "world_config": world_config,
        "chapter_length_hint": chapter_length_hint,
        "tension_threshold": tension_threshold,
        "status": "initialized",
    })

    return jsonify({
        "session_id": session_id,
        "world": world_config,
        "chapter_plans": [p.to_dict() for p in chapter_plans],
        "core_characters": core_characters,
        "status": "initialized",
    })


# ═══════════════════════════════════════════════════
# /generate-chapter  (scene-by-scene pipeline)
# ═══════════════════════════════════════════════════

@story_bp.route("/generate-chapter", methods=["POST"])
def generate_chapter():
    """Generate the next story segment scene-by-scene.

    Stops at a tension-based decision point and emits a `decision_point` SSE event.
    Body: { session_id, user_input? }
    """
    data = request.get_json() or {}
    session_id = data.get("session_id", "")
    user_input = data.get("user_input", "")
    character_pool = data.get("character_pool")       # optional list of char IDs
    relationships   = data.get("relationships") or []  # [{fromId,toId,label,fromName,toName}]

    story = _stories.get(session_id)
    if not story:
        return jsonify({"error": "Session not found. Call /api/story/start first."}), 404

    session = get_session(session_id)
    chapter_length_hint = (session or {}).get("chapter_length_hint", "medium")
    tension_threshold = float((session or {}).get("tension_threshold", TENSION_THRESHOLD))

    chapter_index = len(story.chapters)

    # Auto-extend chapter plans when user provides a branch choice beyond initial plans
    if chapter_index >= len(story.chapter_plans):
        if user_input:
            new_plan = extend_story(
                world_config=story.world_config,
                characters=story.all_characters,
                previous_chapters=[c.to_dict() for c in story.chapters],
                user_choice=user_input,
                theme=story.theme,
                next_chapter_number=chapter_index + 1,
            )
            story.chapter_plans.append(new_plan)
        else:
            return jsonify({"error": "All chapters generated. Provide user_input to continue.", "status": "completed"})

    plan = story.chapter_plans[chapter_index]
    accept = request.headers.get("Accept", "")

    # Filter characters by pool if provided
    if character_pool:
        pool_set = {str(i) for i in character_pool}
        active_chars = [c for c in story.all_characters if str(c.get("id", "")) in pool_set] or story.all_characters
    else:
        active_chars = story.all_characters

    if "text/event-stream" in accept:
        return Response(
            stream_with_context(_chapter_stream(
                story, plan, chapter_index, user_input,
                chapter_length_hint, tension_threshold,
                active_chars=active_chars,
                relationships=relationships,
            )),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Non-streaming fallback
    chapter = _run_chapter_pipeline(
        story, plan, chapter_index, user_input, chapter_length_hint, tension_threshold,
        active_chars=active_chars, relationships=relationships,
    )
    return jsonify({
        "chapter": chapter.to_dict(),
        "chapter_number": chapter_index + 1,
        "status": story.status,
        "decision_point": chapter.decision_scene is not None,
    })


# ═══════════════════════════════════════════════════
# Scene-by-scene SSE stream
# ═══════════════════════════════════════════════════

def _chapter_stream(story, plan, chapter_index, user_input,
                    chapter_length_hint, tension_threshold, active_chars=None, relationships=None):
    chapter_num = chapter_index + 1
    all_chars = active_chars if active_chars else story.all_characters
    relationships = relationships or []

    yield _sse("progress", {"step": "planning", "message": "Director planning scenes…", "progress": 5})

    # ── Plan scenes ──
    scene_plans = plan_scenes(
        world_config=story.world_config,
        characters=all_chars,
        theme=story.theme,
        chapter_number=chapter_num,
        user_choice=user_input,
        previous_context=_prev_prose(story),
        tension_threshold=tension_threshold,
        relationships=relationships,
    )

    yield _sse("log", {
        "sender": "🎬 Director",
        "cls": "director",
        "text": f"Planned {len(scene_plans)} scenes · decision point at scene "
                + str(next((p.scene_number for p in scene_plans if p.is_decision_point), "none")),
    })

    scenes_generated: list[Scene] = []
    decision_scene_num = None

    for scene_plan in scene_plans:
        yield _sse("progress", {
            "step": "scene",
            "message": f"Scene {scene_plan.scene_number}: {scene_plan.title}…",
            "progress": 5 + int(scene_plan.scene_number / len(scene_plans) * 60),
            "tension": scene_plan.tension_level,
            "scene_number": scene_plan.scene_number,
            "scene_title": scene_plan.title,
        })

        # Filter relevant characters for this scene
        involved_ids = scene_plan.involved_characters
        if involved_ids:
            scene_chars = [c for c in all_chars if c["id"] in involved_ids]
            if not scene_chars:
                scene_chars = all_chars
        else:
            scene_chars = all_chars

        # ── Phase 1: Director gathers private intel ──
        yield _sse("log", {
            "sender": "🔍 Director",
            "cls": "director",
            "text": f"Querying private states for scene {scene_plan.scene_number}…",
        })

        private_intel = gather_all_private_states(
            characters=scene_chars,
            scene_description=scene_plan.description,
            story_context=_prev_prose(story, 400),
        )

        for char_id, intel in private_intel.items():
            char_name = intel.get("name", char_id)
            yield _sse("log", {
                "sender": f"🔒 {char_name}",
                "cls": f"char-{char_id}",
                "text": f"[Private → Director] {intel.get('private_state', '')}",
            })

        # ── Phase 2: Director issues instructions ──
        directions = direct_scene(
            world_config=story.world_config,
            characters=scene_chars,
            scene_plan=scene_plan,
            private_intel=private_intel,
            previous_context=_prev_prose(story, 400),
            chapter_number=chapter_num,
            total_chapters=len(story.chapters),
            relationships=relationships,
        )

        yield _sse("log", {
            "sender": "🎬 Director",
            "cls": "director",
            "text": directions.get("tension_driver", "Directions issued."),
        })

        # ── Character actions ──
        actions = []
        public_actions = []
        char_instructions = directions.get("character_instructions", {})

        for i, char in enumerate(scene_chars):
            char_id = char.get("id", str(i))
            instruction = char_instructions.get(char_id, {
                "private_instruction": "Follow your instincts and express your character fully.",
                "emotional_goal": "Show your authentic self.",
                "action_hint": "React naturally to the scene.",
                "interaction_target": "Those around you",
            })

            action = generate_character_action(
                character=char,
                world_config=story.world_config,
                director_instruction=instruction,
                scene_setting=directions.get("scene_setup", scene_plan.description),
                other_characters_public=public_actions,
                scene_tension=scene_plan.tension_level,
            )
            actions.append(action)
            public_actions.append({
                "name": char["name"],
                "public_action": action.public_action,
                "dialogue": action.dialogue,
            })

            char.setdefault("memory", []).append({
                "chapter": chapter_num,
                "scene": scene_plan.scene_number,
                "public_action": action.public_action,
                "private_thought": action.private_thought,
            })

            display_text = action.dialogue if action.dialogue else action.public_action
            yield _sse("log", {
                "sender": f"🎭 {char['name']}",
                "cls": f"char-{char_id}",
                "text": display_text,
            })

        # ── Compose scene prose ──
        yield _sse("progress", {
            "step": "composing",
            "message": f"Writing scene {scene_plan.scene_number}…",
            "progress": 5 + int(scene_plan.scene_number / len(scene_plans) * 60) + 10,
            "tension": scene_plan.tension_level,
        })

        prose = compose_scene(
            scene_plan=scene_plan,
            scene_setup=directions.get("scene_setup", ""),
            atmosphere=directions.get("atmosphere", ""),
            character_actions=actions,
            world_config=story.world_config,
            chapter_number=chapter_num,
            therapeutic_intention=directions.get("therapeutic_intention", ""),
            chapter_length_hint=chapter_length_hint,
            is_decision_point=scene_plan.is_decision_point,
        )

        scene = Scene(
            scene_number=scene_plan.scene_number,
            title=scene_plan.title,
            prose=prose,
            tension_level=scene_plan.tension_level,
            is_decision_point=scene_plan.is_decision_point,
            character_actions=actions,
        )
        scenes_generated.append(scene)

        # Emit scene prose
        yield _sse("scene", {
            "scene_number": scene_plan.scene_number,
            "scene_title": scene_plan.title,
            "prose": prose,
            "tension_level": scene_plan.tension_level,
            "is_decision_point": scene_plan.is_decision_point,
        })

        # Stop at decision point
        if scene_plan.is_decision_point:
            decision_scene_num = scene_plan.scene_number
            log.info("Decision point reached at scene %d (tension=%.2f)",
                     scene_plan.scene_number, scene_plan.tension_level)
            break

    # ── Safety check on full chapter prose ──
    yield _sse("progress", {"step": "safety", "message": "Safety check…", "progress": 88})
    full_prose = "\n\n".join(s.prose for s in scenes_generated)
    safety_result = check_safety(full_prose)

    yield _sse("log", {
        "sender": "🛡 Safety",
        "cls": "safety",
        "text": f"Safety: {safety_result['safety_score']:.2f} · Therapeutic: {safety_result['therapeutic_score']:.2f}",
    })

    # ── Build chapter ──
    chapter = Chapter(
        chapter_number=chapter_num,
        title=plan.title,
        scenes=scenes_generated,
        safety_score=safety_result.get("safety_score", 1.0),
        therapeutic_notes=safety_result.get("recommendations", ""),
        decision_scene=decision_scene_num,
    )
    story.chapters.append(chapter)
    story.status = "awaiting_choice" if decision_scene_num else "generating"

    yield _sse("progress", {"step": "done", "message": "Done!", "progress": 100})
    yield _sse("chapter", {
        "chapter": chapter.to_dict(),
        "chapter_number": chapter_num,
        "safety": safety_result,
        "status": story.status,
        "decision_point": decision_scene_num is not None,
        "scenes_generated": len(scenes_generated),
    })


def _run_chapter_pipeline(story, plan, chapter_index, user_input,
                           chapter_length_hint, tension_threshold, active_chars=None, relationships=None):
    """Non-streaming chapter generation."""
    chapter_num = chapter_index + 1
    all_chars = active_chars if active_chars else story.all_characters
    relationships = relationships or []

    scene_plans = plan_scenes(
        world_config=story.world_config,
        characters=all_chars,
        theme=story.theme,
        chapter_number=chapter_num,
        user_choice=user_input,
        previous_context=_prev_prose(story),
        tension_threshold=tension_threshold,
    )

    scenes_generated = []
    decision_scene_num = None

    for scene_plan in scene_plans:
        private_intel = gather_all_private_states(
            scene_chars := [c for c in all_chars if not scene_plan.involved_characters or c["id"] in scene_plan.involved_characters] or all_chars,
            scene_plan.description,
            _prev_prose(story, 400),
        )

        directions = direct_scene(
            world_config=story.world_config,
            characters=scene_chars,
            scene_plan=scene_plan,
            private_intel=private_intel,
            previous_context=_prev_prose(story, 400),
            chapter_number=chapter_num,
            total_chapters=len(story.chapters),
        )

        actions = []
        public_actions = []
        for i, char in enumerate(scene_chars):
            instruction = directions.get("character_instructions", {}).get(char["id"], {})
            action = generate_character_action(
                character=char,
                world_config=story.world_config,
                director_instruction=instruction,
                scene_setting=directions.get("scene_setup", ""),
                other_characters_public=public_actions,
                scene_tension=scene_plan.tension_level,
            )
            actions.append(action)
            public_actions.append({"name": char["name"], "public_action": action.public_action, "dialogue": action.dialogue})
            char.setdefault("memory", []).append({"chapter": chapter_num, "scene": scene_plan.scene_number, "public_action": action.public_action, "private_thought": action.private_thought})

        prose = compose_scene(
            scene_plan=scene_plan,
            scene_setup=directions.get("scene_setup", ""),
            atmosphere=directions.get("atmosphere", ""),
            character_actions=actions,
            world_config=story.world_config,
            chapter_number=chapter_num,
            therapeutic_intention=directions.get("therapeutic_intention", ""),
            chapter_length_hint=chapter_length_hint,
            is_decision_point=scene_plan.is_decision_point,
        )

        scenes_generated.append(Scene(
            scene_number=scene_plan.scene_number,
            title=scene_plan.title,
            prose=prose,
            tension_level=scene_plan.tension_level,
            is_decision_point=scene_plan.is_decision_point,
            character_actions=actions,
        ))

        if scene_plan.is_decision_point:
            decision_scene_num = scene_plan.scene_number
            break

    full_prose = "\n\n".join(s.prose for s in scenes_generated)
    safety_result = check_safety(full_prose)

    chapter = Chapter(
        chapter_number=chapter_num,
        title=plan.title,
        scenes=scenes_generated,
        safety_score=safety_result.get("safety_score", 1.0),
        therapeutic_notes=safety_result.get("recommendations", ""),
        decision_scene=decision_scene_num,
    )
    story.chapters.append(chapter)
    story.status = "awaiting_choice" if decision_scene_num else "generating"
    return chapter


# ═══════════════════════════════════════════════════
# /add-character  — introduce a new character mid-story
# ═══════════════════════════════════════════════════

@story_bp.route("/add-character", methods=["POST"])
def add_character():
    """Add a new story character mid-story.

    Body: { session_id, character: { id, name, personality, background?, role?, color? } }
    """
    data = request.get_json() or {}
    session_id = data.get("session_id", "")
    char_data = data.get("character", {})

    story = _stories.get(session_id)
    if not story:
        return jsonify({"error": "Session not found"}), 404
    if not char_data.get("name") or not char_data.get("personality"):
        return jsonify({"error": "character.name and character.personality are required"}), 400

    char_data.setdefault("id", str(uuid.uuid4())[:8])
    char_data["is_story_character"] = True

    story.story_characters.append(char_data)

    session = get_session(session_id)
    if session:
        session.setdefault("story_characters", []).append(char_data)
        save_session(session_id, session)

    log.info("New story character '%s' added to session %s", char_data["name"], session_id)
    return jsonify({
        "status": "ok",
        "character": char_data,
        "total_characters": len(story.all_characters),
    })


# ═══════════════════════════════════════════════════
# /backtrack  — truncate story to a chapter for re-branching
# ═══════════════════════════════════════════════════

@story_bp.route("/backtrack", methods=["POST"])
def backtrack():
    """Truncate story to a given chapter so user can branch from there.

    Body: { session_id, chapter_number }
    chapter_number is 1-based; chapters after it are removed.
    """
    data = request.get_json() or {}
    session_id = data.get("session_id", "")
    chapter_number = int(data.get("chapter_number", 1))

    story = _stories.get(session_id)
    if not story:
        return jsonify({"error": "Session not found"}), 404

    keep = max(1, chapter_number)
    story.chapters = story.chapters[:keep]
    story.status = "in_progress"
    log.info("Backtrack session %s to chapter %d (%d chapters kept)",
             session_id, chapter_number, len(story.chapters))
    return jsonify({"status": "ok", "chapters_kept": len(story.chapters)})


# ═══════════════════════════════════════════════════
# /generate-choices
# ═══════════════════════════════════════════════════

@story_bp.route("/generate-choices", methods=["POST"])
def generate_choices():
    """Generate 3 branch choices after a decision point.

    Body: { session_id, num_choices? }
    """
    data = request.get_json() or {}
    session_id = data.get("session_id", "")
    num_choices = min(data.get("num_choices", 3), 4)

    story = _stories.get(session_id)
    if not story:
        return jsonify({"error": "Session not found"}), 404
    if not story.chapters:
        return jsonify({"error": "No chapters generated yet"}), 400

    last_ch = story.chapters[-1]
    decision_scene = next(
        (s for s in reversed(last_ch.scenes) if s.is_decision_point), None
    )
    last_prose = decision_scene.prose if decision_scene else last_ch.prose
    world_desc = story.world_config.get("description", "")[:200]
    char_names = ", ".join(c.get("name", "") for c in story.all_characters)
    core_tensions = ", ".join(
        f"{c.get('character_name', c.get('name', '?'))}({c.get('emotional_state', '')})"
        for s in last_ch.scenes
        for c in (a.__dict__ for a in s.character_actions)
        if c.get("emotional_state")
    )

    prompt = (
        f"Story theme: {story.theme}\n"
        f"World: {world_desc}\n"
        f"Characters: {char_names}\n"
        + (f"Current tensions: {core_tensions}\n" if core_tensions else "")
        + f"\nDecision point excerpt (last ~500 chars):\n{last_prose[-500:]}\n\n"
        f"Generate {num_choices} meaningfully distinct choices for what happens next.\n"
        "Each choice should lead the story in a different emotional direction — "
        "vary the tone: e.g. confrontation, escape, revelation, sacrifice, unexpected connection.\n"
        f'Return JSON: {{"choices": [{{"id": "A", "title": "≤6-word dramatic title", '
        '"description": "2 sentences of what happens and how it feels"}}]}}'
    )

    try:
        result = chat_json([{"role": "user", "content": prompt}], temperature=0.95)
        parsed = json.loads(result)
        return jsonify(parsed)
    except Exception as e:
        log.error("generate_choices error: %s", e)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════
# /suggest
# ═══════════════════════════════════════════════════

@story_bp.route("/suggest", methods=["POST"])
def suggest():
    """AI suggestions for title / theme / world keywords.

    Body: { type: "title"|"theme"|"keywords", context: "..." }
    """
    data = request.get_json() or {}
    suggest_type = data.get("type", "title")
    context = data.get("context", "")

    prompts = {
        "title": (
            f"Context: {context}\n"
            "Generate 5 evocative story titles (2–6 words each). "
            'Return JSON: {"suggestions": ["title1", ...]}'
        ),
        "theme": (
            f"Context: {context}\n"
            "Generate 5 compelling story themes or central emotional conflicts (one sentence each). "
            'Return JSON: {"suggestions": ["theme1", ...]}'
        ),
        "keywords": (
            f"Story concept: {context}\n"
            "Generate world-building keywords in 4 categories. "
            'Return JSON: {"categories": [{"name": "Environment", "words": [...]}, '
            '{"name": "Atmosphere", "words": [...]}, '
            '{"name": "Era / Tech", "words": [...]}, '
            '{"name": "Special Elements", "words": [...]}]}'
        ),
    }

    try:
        result = chat_json([{"role": "user", "content": prompts.get(suggest_type, prompts["title"])}], temperature=0.9)
        return jsonify(json.loads(result))
    except Exception as e:
        log.error("suggest error: %s", e)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════
# Misc routes
# ═══════════════════════════════════════════════════

@story_bp.route("/status/<session_id>", methods=["GET"])
def get_status(session_id: str):
    story = _stories.get(session_id)
    if not story:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({
        "session_id": session_id,
        "status": story.status,
        "chapters_generated": len(story.chapters),
        "total_planned": len(story.chapter_plans),
        "core_characters": len(story.core_characters),
        "story_characters": len(story.story_characters),
    })


@story_bp.route("/relationships/<session_id>", methods=["GET"])
def get_relationships(session_id):
    """Extract character relationships from the current story using LLM."""
    story = _stories.get(session_id)
    if not story:
        sess = get_session(session_id)
        if not sess:
            return jsonify({"error": "session not found"}), 404
        story = _stories.get(session_id)
    if not story or not story.chapters:
        return jsonify({"relationships": []})

    # Use last 2 chapters for context
    prose_chunks = []
    for ch in story.chapters[-2:]:
        prose_chunks.append(f"Chapter {ch.chapter_number} — {ch.title}:\n{ch.prose[:600]}")
    prose = "\n\n".join(prose_chunks)

    chars = [{"id": c["id"], "name": c["name"]} for c in story.all_characters]

    prompt = (
        f"Characters: {json.dumps(chars, ensure_ascii=False)}\n\n"
        f"Story excerpt:\n{prose}\n\n"
        "Based on this story, infer the current emotional/social relationship between characters.\n"
        "Each relationship is DIRECTED (A→B reflects A's feeling toward B).\n"
        "If A and B have DIFFERENT feelings toward each other, list them as two separate entries.\n"
        "Use short labels (1-3 words), e.g.: 'trusts', 'secretly loves', 'fears', 'rivals', 'mentors', 'resents'.\n\n"
        "Output JSON:\n"
        '{"relationships": [{"fromId": "id", "toId": "id", "label": "..."}]}\n'
        "Only include relationships clearly shown in the text. Max 12 entries."
    )

    try:
        response = chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        data = json.loads(response)
        rels = data.get("relationships", [])
        # Validate: both ids must be known characters
        known_ids = {str(c["id"]) for c in story.all_characters}
        rels = [
            r for r in rels
            if str(r.get("fromId")) in known_ids and str(r.get("toId")) in known_ids
               and r.get("label")
        ]
        log.info("Extracted %d relationships for session %s", len(rels), session_id)
        return jsonify({"relationships": rels})
    except Exception as e:
        log.error("Relationship extraction failed: %s", e)
        return jsonify({"relationships": []})


@story_bp.route("/generate-avatar", methods=["POST"])
def generate_avatar():
    """Generate a character avatar image using DALL-E 3.

    Body: { character_name, description, style?, api_key? }
    Requires an OpenAI API key (DALL-E 3 is OpenAI-only).
    """
    data = request.get_json() or {}
    description = data.get("description", "").strip()
    character_name = data.get("character_name", "Character").strip()
    style = data.get("style", "fantasy illustration")

    if not description:
        return jsonify({"error": "description is required"}), 400

    # DALL-E 3 must go through OpenAI endpoint
    from app.config import Config
    from openai import OpenAI

    api_key = data.get("api_key") or Config.LLM_API_KEY
    if not api_key:
        return jsonify({"error": "No OpenAI API key configured"}), 400

    prompt = (
        f"Character portrait: {character_name} — {description}. "
        f"Style: {style}, expressive close-up bust portrait, "
        "vivid character design, dramatic atmospheric lighting, "
        "dark moody background with subtle color accent, "
        "high quality digital illustration, cinematic, no text, no watermarks, no borders."
    )

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.openai.com/v1")
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        revised_prompt = getattr(response.data[0], "revised_prompt", prompt)
        log.info("Avatar generated for '%s': %s", character_name, image_url[:60])
        return jsonify({"url": image_url, "revised_prompt": revised_prompt})
    except Exception as e:
        log.error("Avatar generation failed: %s", e)
        return jsonify({"error": str(e)}), 500


@story_bp.route("/user-input", methods=["POST"])
def user_input():
    data = request.get_json() or {}
    session_id = data.get("session_id", "")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400
    if not _stories.get(session_id):
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"status": "accepted", "session_id": session_id})


# ═══════════════════════════════════════════════════
# /generate-branch-previews — 2 actual story prose continuations
# ═══════════════════════════════════════════════════

@story_bp.route("/generate-branch-previews", methods=["POST"])
def generate_branch_previews():
    """Generate 2 distinctly different story prose continuation previews at a decision point.

    Body: { session_id }
    Returns: { previews: [{id, title, prose, tone}, {id, title, prose, tone}] }
    """
    data = request.get_json() or {}
    session_id = data.get("session_id", "")

    story = _stories.get(session_id)
    if not story:
        return jsonify({"error": "Session not found"}), 404
    if not story.chapters:
        return jsonify({"error": "No chapters generated yet"}), 400

    last_ch = story.chapters[-1]
    decision_scene = next(
        (s for s in reversed(last_ch.scenes) if s.is_decision_point), None
    )
    last_prose = decision_scene.prose if decision_scene else last_ch.prose

    world_desc = story.world_config.get("description", "")[:300]
    char_descs = "\n".join(
        f"- {c.get('name')}: {c.get('personality', '')}"
        for c in story.all_characters
    )

    prompt = (
        f"Story theme: {story.theme}\n"
        f"World: {world_desc}\n"
        f"Characters:\n{char_descs}\n\n"
        f"Story so far (last passage):\n{last_prose[-900:]}\n\n"
        "The story has just reached a critical, dramatic turning point. "
        "Write 2 DISTINCTLY DIFFERENT continuations — Branch A and Branch B.\n"
        "Each branch MUST:\n"
        "- Be 250–320 words of vivid, literary prose in the SAME style as the story\n"
        "- Take the story in a different emotional/narrative direction\n"
        "- Have a short dramatic title (≤6 words)\n"
        "- Have a one-word tone descriptor\n\n"
        "Vary the directions: e.g., confrontation vs. escape, revelation vs. sacrifice, "
        "darkness vs. unexpected hope, external action vs. internal revelation, "
        "acceptance vs. resistance.\n\n"
        'Return ONLY this JSON (no markdown, no extra text):\n'
        '{"previews": ['
        '{"id": "A", "title": "...", "tone": "one-word", "prose": "250-320 word continuation"},'
        '{"id": "B", "title": "...", "tone": "one-word", "prose": "250-320 word continuation"}'
        ']}'
    )

    try:
        result = chat_json([{"role": "user", "content": prompt}], temperature=0.93)
        parsed = json.loads(result)
        return jsonify(parsed)
    except Exception as e:
        log.error("generate_branch_previews error: %s", e)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════
# /director-chat — user talks to the director, gets custom continuation
# ═══════════════════════════════════════════════════

@story_bp.route("/director-chat", methods=["POST"])
def director_chat():
    """User sends a creative direction to the Director, who responds + writes a preview.

    Body: { session_id, message }
    Returns: { director_response, title, prose, tone }
    """
    data = request.get_json() or {}
    session_id = data.get("session_id", "")
    user_message = data.get("message", "").strip()

    story = _stories.get(session_id)
    if not story:
        return jsonify({"error": "Session not found"}), 404
    if not user_message:
        return jsonify({"error": "message is required"}), 400

    last_ch = story.chapters[-1] if story.chapters else None
    last_prose = ""
    if last_ch:
        decision_scene = next(
            (s for s in reversed(last_ch.scenes) if s.is_decision_point), None
        )
        last_prose = (decision_scene.prose if decision_scene else last_ch.prose)[-700:]

    world_desc = story.world_config.get("description", "")[:250]
    char_descs = "\n".join(
        f"- {c.get('name')}: {c.get('personality', '')}"
        for c in story.all_characters
    )

    system_prompt = (
        "You are the Director — a master storyteller in the tradition of Ingmar Bergman and Wong Kar-wai. "
        "A collaborator is giving you creative direction for their therapeutic narrative. "
        "You receive their instruction, briefly acknowledge it in your Director's voice (1–2 sentences, "
        "warm but cinematic), then write a vivid ~300-word prose continuation that honors their intent "
        "while maintaining narrative quality. Maintain literary prose style throughout.\n"
        f"Story theme: {story.theme}\n"
        f"World: {world_desc}\n"
        f"Characters:\n{char_descs}"
    )

    user_prompt = (
        f"Story so far (last passage):\n{last_prose}\n\n"
        f"My direction for what should happen next: {user_message}\n\n"
        "Please acknowledge my direction briefly (as the Director) and write a ~300-word "
        "continuation that fulfills it.\n"
        'Return ONLY this JSON (no markdown, no extra text):\n'
        '{"director_response": "1-2 sentence acknowledgment as the Director", '
        '"title": "≤6-word dramatic title", '
        '"tone": "one-word tone", '
        '"prose": "~300-word continuation prose"}'
    )

    try:
        result = chat_json(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.88,
        )
        parsed = json.loads(result)
        return jsonify(parsed)
    except Exception as e:
        log.error("director_chat error: %s", e)
        return jsonify({"error": str(e)}), 500


@story_bp.route("/export/<session_id>", methods=["GET"])
def export_story(session_id: str):
    story = _stories.get(session_id)
    if not story:
        return jsonify({"error": "Session not found"}), 404

    fmt = request.args.get("format", "json")
    if fmt == "text":
        text = f"# {story.theme}\n\n"
        for ch in story.chapters:
            text += f"## Chapter {ch.chapter_number}: {ch.title}\n\n"
            for s in ch.scenes:
                if len(ch.scenes) > 1:
                    text += f"### {s.title}\n\n"
                text += s.prose + "\n\n"
        return Response(text, mimetype="text/plain; charset=utf-8")

    return jsonify(story.to_dict())
