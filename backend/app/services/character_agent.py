"""Character Agent — each character independently generates actions/dialogue/thoughts."""
import json
from app.utils.llm_client import chat_json
from app.utils.logger import get_logger
from app.models.story import CharacterAction

log = get_logger(__name__)

CHARACTER_SYSTEM_PROMPT = """You are a Character Agent in a therapeutic story simulation.
You embody a specific character and generate their actions, dialogue, and inner thoughts.

Important rules:
1. Stay in character — your personality, background, and role define how you respond
2. You have PUBLIC actions (others can see) and PRIVATE thoughts (only the Director sees)
3. Follow the Director's private instructions but interpret them through your character's lens
4. Your responses should feel authentic and emotionally honest
5. This is a therapeutic story — your character's journey should have psychological depth

Output a JSON object:
{
  "public_action": "你的角色在这一章做了什么（其他角色可以看到）",
  "private_thought": "你的角色内心真实的想法和感受（只有导演知道）",
  "dialogue": "你的角色说的话（可以是对特定角色说的，也可以是独白）",
  "emotional_state": "当前情感状态的关键词",
  "growth_moment": "这个角色在本章是否有成长或转变的瞬间（如果有的话描述）"
}

Respond ONLY with the JSON object. Write in Chinese."""


def generate_character_action(
    character: dict,
    world_config: dict,
    director_instruction: dict,
    scene_setting: str,
    other_characters_public: list[dict] = None,
) -> CharacterAction:
    """Generate a character's response for a chapter (LLM Call #4)."""
    log.info("Character agent: %s (%s)", character["name"], character["id"])

    # Build context about other characters' public actions
    others_context = ""
    if other_characters_public:
        for other in other_characters_public:
            others_context += f"\n- {other['name']}: {other.get('public_action', '（尚未行动）')}"
            if other.get("dialogue"):
                others_context += f'\n  说: "{other["dialogue"]}"'

    memory_context = ""
    if character.get("memory"):
        for mem in character["memory"][-3:]:  # last 3 memories
            memory_context += f"\n- {mem.get('public_action', '')}"

    user_msg = f"""你是「{character['name']}」。

性格: {character['personality']}
背景: {character.get('background', '未知')}
角色定位: {character.get('role', '角色')}

场景: {scene_setting}

导演给你的私密指令:
- 指令: {director_instruction.get('private_instruction', '自由发挥')}
- 情感目标: {director_instruction.get('emotional_goal', '展现真实的自我')}
- 互动建议: {director_instruction.get('interaction_hints', '与他人交流')}

{f"其他角色的行动:{others_context}" if others_context else "你是第一个行动的角色。"}

{f"你的过往记忆:{memory_context}" if memory_context else "这是你在故事中的第一次出场。"}

请以你的角色身份回应当前场景。"""

    response = chat_json(
        messages=[
            {"role": "system", "content": CHARACTER_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.85,
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        log.error("Failed to parse character response for %s", character["name"])
        data = {
            "public_action": f"{character['name']}静静地站在那里，注视着周围的一切。",
            "private_thought": "我需要时间来理解这里正在发生的一切。",
            "dialogue": "",
        }

    action = CharacterAction(
        character_id=character["id"],
        character_name=character["name"],
        public_action=data.get("public_action", ""),
        private_thought=data.get("private_thought", ""),
        dialogue=data.get("dialogue", ""),
    )

    log.info("Character %s action generated", character["name"])
    return action
