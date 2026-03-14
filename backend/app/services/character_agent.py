"""Character Agent — generates per-character actions and responds to Director queries.

Each character has two modes:
  1. respond_to_director_query(): reveal private state to Director only (Phase 1)
  2. generate_character_action(): produce public action based on Director's instruction (Phase 2)
"""
import json
from app.utils.llm_client import chat_json
from app.utils.logger import get_logger
from app.models.story import CharacterAction

log = get_logger(__name__)

# ─────────────────────────────────────────────
# Phase 2: Public action generation
# ─────────────────────────────────────────────

CHARACTER_ACTION_PROMPT = """You are a Character Agent in a therapeutic story simulation.
You embody a specific character and generate their public actions, dialogue, and surfaced thoughts.

Rules:
1. Stay completely in character — your personality and background define every choice
2. You have PRIVATE instructions from the Director (only you know these)
3. Your PUBLIC actions are visible to all other characters and the audience
4. This is a therapeutic story — your actions should carry emotional weight
5. Show, don't tell: convey inner states through gesture, action, and subtext

Output JSON:
{
  "public_action": "what your character visibly does (2-4 sentences)",
  "private_thought": "your character's unspoken inner monologue (visible to narrator, not characters)",
  "dialogue": "exact words your character says (empty string if silent)",
  "emotional_state": "one or two keywords for current emotional state",
  "growth_moment": "if this scene marks a shift in your character's perspective, describe it briefly; else empty"
}
Respond ONLY with the JSON. Write in Chinese."""


def generate_character_action(
    character: dict,
    world_config: dict,
    director_instruction: dict,
    scene_setting: str,
    other_characters_public: list[dict] = None,
    scene_tension: float = 0.5,
) -> CharacterAction:
    """Generate a character's public action for a scene (Director Phase 2 output)."""
    log.info("Character '%s' acting in scene (tension=%.2f)", character["name"], scene_tension)

    others_ctx = ""
    if other_characters_public:
        for other in other_characters_public:
            others_ctx += f"\n- {other['name']}: {other.get('public_action', '（尚未行动）')}"
            if other.get("dialogue"):
                others_ctx += f'\n  说: "{other["dialogue"]}"'

    memory_ctx = ""
    if character.get("memory"):
        for mem in character["memory"][-3:]:
            memory_ctx += f"\n- 第{mem.get('chapter', '?')}章: {mem.get('public_action', '')[:80]}"

    is_new = character.get("is_story_character", False)
    char_intro = (
        "（你是刚刚加入故事的新角色，这是你第一次出场，注意给读者留下鲜明印象。）"
        if is_new else ""
    )

    user_msg = (
        f"你是「{character['name']}」。{char_intro}\n"
        f"性格: {character['personality']}\n"
        f"背景: {character.get('background', '未知')}\n"
        f"角色定位: {character.get('role', '角色')}\n\n"
        f"当前场景: {scene_setting}\n"
        f"场景张力: {scene_tension:.0%}\n\n"
        f"导演给你的私密指令:\n"
        f"- 核心指令: {director_instruction.get('private_instruction', '自由发挥')}\n"
        f"- 情感目标: {director_instruction.get('emotional_goal', '展现真实的自我')}\n"
        f"- 行动建议: {director_instruction.get('action_hint', '自然互动')}\n"
        f"- 互动目标: {director_instruction.get('interaction_target', '身边的人')}\n\n"
        + (f"其他角色的公开行动:{others_ctx}\n\n" if others_ctx else "你是第一个行动的角色。\n\n")
        + (f"你的过往记忆:{memory_ctx}\n\n" if memory_ctx else "")
        + "请以你的角色身份回应当前场景。"
    )

    response = chat_json(
        messages=[
            {"role": "system", "content": CHARACTER_ACTION_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.85,
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        log.error("Failed to parse character action for '%s'", character["name"])
        data = {
            "public_action": f"{character['name']}静静地站在那里，注视着周围的一切。",
            "private_thought": "我需要时间来理解这里正在发生的一切。",
            "dialogue": "",
            "emotional_state": "沉默",
            "growth_moment": "",
        }

    action = CharacterAction(
        character_id=character["id"],
        character_name=character["name"],
        public_action=data.get("public_action", ""),
        private_thought=data.get("private_thought", ""),
        dialogue=data.get("dialogue", ""),
        emotional_state=data.get("emotional_state", ""),
        growth_moment=data.get("growth_moment", ""),
    )

    log.info("Character '%s' action generated (emotion: %s)", character["name"], action.emotional_state)
    return action
