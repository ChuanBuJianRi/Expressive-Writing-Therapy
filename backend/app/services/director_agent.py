"""Director Agent — two-phase orchestrator.

Phase 1 — Intelligence Gathering:
  Director broadcasts a private query to each character agent,
  learning their hidden fears, desires, and current emotional state.

Phase 2 — Direction:
  Armed with complete private knowledge, Director issues
  per-character instructions and plans the dramatic arc.
"""
import json
from app.utils.llm_client import chat_json
from app.utils.logger import get_logger
from app.models.story import ScenePlan

log = get_logger(__name__)

# ─────────────────────────────────────────────
# Scene Planning
# ─────────────────────────────────────────────

SCENE_PLANNER_PROMPT = """You are the Director of a therapeutic story simulation.
Plan a sequence of 3-5 scenes for the next story segment.

Rules:
- Each scene has a tension_level (0.0–1.0): 0 = calm/reflective, 1.0 = crisis/peak conflict
- A scene with tension_level > 0.75 AND is_decision_point = true is where the story PAUSES
  for the user to choose what happens next. Mark AT MOST ONE scene as is_decision_point.
- Tension should rise naturally — don't peak in scene 1.
- The decision point should feel like a genuine narrative crossroads, not an arbitrary stop.
- involved_characters: list only the character IDs relevant to this scene.

Output JSON:
{
  "scenes": [
    {
      "scene_number": 1,
      "title": "场景标题",
      "description": "场景内容描述",
      "tension_level": 0.3,
      "is_decision_point": false,
      "involved_characters": ["char_id_1", "char_id_2"]
    }
  ]
}
Respond ONLY with the JSON."""


def plan_scenes(
    world_config: dict,
    characters: list[dict],
    theme: str,
    chapter_number: int,
    user_choice: str = "",
    previous_context: str = "",
    tension_threshold: float = 0.72,
) -> list[ScenePlan]:
    """Director plans scenes for the next story segment."""
    log.info("Planning scenes for chapter %d (user_choice=%s)", chapter_number, bool(user_choice))

    char_list = "\n".join(
        f"- [{c['id']}] {c['name']} ({c.get('role', '')}): {c['personality'][:80]}"
        for c in characters
    )

    user_msg = (
        f"故事主题: {theme}\n"
        f"当前是第 {chapter_number} 章\n"
        f"张力阈值（超过此值且is_decision_point=true时暂停）: {tension_threshold}\n\n"
        f"世界: {world_config.get('name', '')} — {world_config.get('description', '')[:200]}\n\n"
        f"角色:\n{char_list}\n\n"
        + (f"用户选择的方向:\n{user_choice}\n\n" if user_choice else "")
        + (f"前情摘要:\n{previous_context[:600]}\n\n" if previous_context else "")
        + "请规划接下来的 3-5 个场景，确保有一个自然的张力高峰作为决策点。"
    )

    response = chat_json(
        messages=[
            {"role": "system", "content": SCENE_PLANNER_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.75,
    )

    try:
        data = json.loads(response)
        scenes_data = data.get("scenes", [])
    except json.JSONDecodeError:
        log.error("Failed to parse scene plan")
        scenes_data = _default_scenes(chapter_number)

    plans = []
    for s in scenes_data:
        plan = ScenePlan(
            scene_number=s.get("scene_number", len(plans) + 1),
            title=s.get("title", f"场景 {len(plans)+1}"),
            description=s.get("description", ""),
            tension_level=float(s.get("tension_level", 0.4)),
            is_decision_point=bool(s.get("is_decision_point", False)),
            involved_characters=s.get("involved_characters", [c["id"] for c in characters]),
        )
        # Auto-promote highest tension scene to decision point if none marked
        plans.append(plan)

    if not any(p.is_decision_point for p in plans):
        # Mark the scene with highest tension as decision point
        highest = max(plans, key=lambda p: p.tension_level)
        if highest.tension_level >= tension_threshold:
            highest.is_decision_point = True

    log.info("Planned %d scenes, decision point at scene %s",
             len(plans),
             next((p.scene_number for p in plans if p.is_decision_point), "none"))
    return plans


# ─────────────────────────────────────────────
# Phase 1: Private Character Query
# ─────────────────────────────────────────────

CHARACTER_QUERY_PROMPT = """You are a character in a therapeutic story simulation.
The Director (only) is asking about your PRIVATE inner state. Be completely honest.
Other characters CANNOT see this response.

Output JSON:
{
  "private_state": "your current true emotional state in 1-2 sentences",
  "hidden_desire": "what you secretly want in this moment",
  "hidden_fear": "what you are afraid of but haven't shown to others",
  "secret": "something you know or hold that others don't (can be 'none')",
  "relationship_tensions": "how you privately feel about each other character (brief)"
}
Respond ONLY with the JSON."""


def query_character_private_state(
    character: dict,
    scene_description: str,
    story_context: str = "",
) -> dict:
    """Director privately queries a single character for their hidden state."""
    user_msg = (
        f"你是「{character['name']}」。\n"
        f"性格: {character['personality']}\n"
        f"背景: {character.get('background', '未知')}\n\n"
        f"当前场景: {scene_description}\n\n"
        + (f"故事背景:\n{story_context[:400]}\n\n" if story_context else "")
        + "导演私下询问你的真实内心状态。请完全坦诚地回答。"
    )

    response = chat_json(
        messages=[
            {"role": "system", "content": CHARACTER_QUERY_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.82,
    )

    try:
        state = json.loads(response)
    except json.JSONDecodeError:
        state = {
            "private_state": "内心复杂，难以言说。",
            "hidden_desire": "渴望被理解。",
            "hidden_fear": "害怕失去。",
            "secret": "none",
            "relationship_tensions": "对身边的人感情复杂。",
        }

    log.debug("Private state queried for %s", character["name"])
    return state


def gather_all_private_states(
    characters: list[dict],
    scene_description: str,
    story_context: str = "",
) -> dict:
    """Director gathers private states from ALL characters (Phase 1)."""
    private_intel = {}
    for char in characters:
        state = query_character_private_state(char, scene_description, story_context)
        private_intel[char["id"]] = {
            "name": char["name"],
            **state,
        }
    log.info("Director gathered private intel from %d characters", len(private_intel))
    return private_intel


# ─────────────────────────────────────────────
# Phase 2: Direction (with full private knowledge)
# ─────────────────────────────────────────────

DIRECTOR_PROMPT = """You are the Director Agent of a therapeutic story simulation.
You have just received PRIVATE intelligence from all characters (their hidden states, fears, desires).
Use this information to craft targeted, dramatically effective instructions for each character.

Your instructions must:
1. Be specific to each character's private state — exploit or support their inner tensions
2. Drive the scene toward its planned tension level
3. Create meaningful character interactions that reveal truth gradually
4. Never directly expose one character's secrets to another — let it emerge through action
5. Maintain therapeutic value: even conflict should open doors to self-understanding

Output JSON:
{
  "scene_setup": "Director's vision for this scene in 2-3 sentences",
  "atmosphere": "the physical and emotional atmosphere to establish",
  "character_instructions": {
    "<character_id>": {
      "private_instruction": "specific directive using their hidden state",
      "emotional_goal": "the emotional arc for this character in this scene",
      "action_hint": "suggested concrete action or gesture",
      "interaction_target": "which character(s) to engage with and how"
    }
  },
  "tension_driver": "the key event or revelation that raises tension in this scene",
  "therapeutic_intention": "what insight or healing this scene offers the reader"
}
Respond ONLY with the JSON."""


def direct_scene(
    world_config: dict,
    characters: list[dict],
    scene_plan: ScenePlan,
    private_intel: dict,
    previous_context: str = "",
) -> dict:
    """Phase 2: Director issues per-character instructions using private knowledge."""
    log.info(
        "Director directing scene %d '%s' (tension=%.2f)",
        scene_plan.scene_number,
        scene_plan.title,
        scene_plan.tension_level,
    )

    intel_summary = ""
    for char_id, intel in private_intel.items():
        intel_summary += (
            f"\n[{intel['name']}的私人状态]\n"
            f"  真实感受: {intel.get('private_state', '')}\n"
            f"  隐藏渴望: {intel.get('hidden_desire', '')}\n"
            f"  内心恐惧: {intel.get('hidden_fear', '')}\n"
            f"  秘密: {intel.get('secret', 'none')}\n"
        )

    char_list = "\n".join(
        f"- [{c['id']}] {c['name']}: {c.get('role', '')}"
        for c in characters
    )

    user_msg = (
        f"场景: 第{scene_plan.scene_number}场 —「{scene_plan.title}」\n"
        f"场景描述: {scene_plan.description}\n"
        f"目标张力: {scene_plan.tension_level:.0%}\n"
        f"是否决策点: {'是（这场戏将以一个戏剧性时刻结束，让读者做出选择）' if scene_plan.is_decision_point else '否'}\n\n"
        f"角色列表:\n{char_list}\n\n"
        f"导演掌握的私密情报:{intel_summary}\n\n"
        + (f"前情:\n{previous_context[:400]}\n\n" if previous_context else "")
        + "请利用所有私密信息，为每个角色发出有针对性的指令。"
    )

    response = chat_json(
        messages=[
            {"role": "system", "content": DIRECTOR_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.78,
    )

    try:
        directions = json.loads(response)
    except json.JSONDecodeError:
        log.error("Failed to parse director output for scene %d", scene_plan.scene_number)
        directions = _fallback_directions(characters, scene_plan)

    return directions


def _fallback_directions(characters: list[dict], scene_plan: ScenePlan) -> dict:
    return {
        "scene_setup": scene_plan.description,
        "atmosphere": "情感氛围微妙复杂",
        "character_instructions": {
            c["id"]: {
                "private_instruction": "按照你的直觉行动，展现真实自我。",
                "emotional_goal": "在这一场景中有所感悟。",
                "action_hint": "自然地与周围人互动。",
                "interaction_target": "身边的人",
            }
            for c in characters
        },
        "tension_driver": "一个意想不到的瞬间",
        "therapeutic_intention": "帮助读者与角色共情",
    }


def _default_scenes(chapter_number: int) -> list[dict]:
    return [
        {"scene_number": 1, "title": "相遇", "description": "角色在特定地点相聚", "tension_level": 0.3, "is_decision_point": False, "involved_characters": []},
        {"scene_number": 2, "title": "交流", "description": "角色之间产生对话和摩擦", "tension_level": 0.55, "is_decision_point": False, "involved_characters": []},
        {"scene_number": 3, "title": "冲突", "description": "隐藏的矛盾浮出水面", "tension_level": 0.78, "is_decision_point": True, "involved_characters": []},
    ]
