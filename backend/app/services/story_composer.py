"""Story Composer — merges all character outputs into coherent narrative prose."""
from app.utils.llm_client import chat
from app.utils.logger import get_logger
from app.models.story import CharacterAction

log = get_logger(__name__)

COMPOSER_SYSTEM_PROMPT = """You are the Story Composer for a therapeutic story simulation system.
Your job is to take raw character actions, dialogue, and inner thoughts, and weave them into
beautiful, cohesive narrative prose.

Writing guidelines:
1. Write in Chinese (中文), in a literary but accessible style
2. Use third-person limited or omniscient narration
3. Seamlessly integrate each character's actions and dialogue
4. Reveal private thoughts as inner monologue (using italics style markers)
5. Create vivid scene descriptions that enhance the emotional atmosphere
6. The narrative should flow naturally — this is a story, not a log
7. Maintain therapeutic intent — the prose should invite reflection
8. Each chapter should be 400-800 Chinese characters

Do NOT output JSON. Write the story prose directly."""


def compose_chapter(
    chapter_plan: dict,
    scene_setting: str,
    character_actions: list[CharacterAction],
    world_config: dict,
    chapter_number: int,
    therapeutic_intention: str = "",
) -> str:
    """Compose a chapter from character actions (LLM Call #5)."""
    log.info("Composing chapter %d: %s", chapter_number, chapter_plan.get("title", ""))

    actions_text = ""
    for action in character_actions:
        actions_text += f"\n【{action.character_name}】\n"
        actions_text += f"  行动: {action.public_action}\n"
        actions_text += f"  内心: {action.private_thought}\n"
        if action.dialogue:
            actions_text += f"  台词: \"{action.dialogue}\"\n"

    user_msg = f"""请将以下角色行动整合为一段连贯的故事叙述。

章节信息:
- 第{chapter_number}章: {chapter_plan.get('title', '')}
- 大纲: {chapter_plan.get('summary', '')}
- 场景: {scene_setting}
- 治疗意图: {therapeutic_intention}

世界: {world_config.get('name', '')} — {world_config.get('description', '')}

角色行动:
{actions_text}

请写出这一章的故事正文（400-800字中文）。要求文学性强、情感细腻、叙事流畅。
将角色的内心想法自然地融入叙事中，用微妙的方式呈现，而非直接陈述。"""

    prose = chat(
        messages=[
            {"role": "system", "content": COMPOSER_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.85,
        max_tokens=2048,
    )

    log.info("Chapter %d composed: %d chars", chapter_number, len(prose))
    return prose
