"""Story Composer — weaves character actions into narrative prose, scene by scene."""
from app.utils.llm_client import chat
from app.utils.logger import get_logger
from app.models.story import CharacterAction, ScenePlan

log = get_logger(__name__)

COMPOSER_SYSTEM_PROMPT = """You are the Story Composer for a therapeutic narrative simulation.
Transform raw character actions and Director notes into beautiful literary prose.

Writing guidelines:
1. Write in Chinese (中文), literary but accessible — aim for the quality of contemporary literary fiction
2. Third-person narration; weave internal monologue subtly into the flow
3. Each character's actions, gestures, and words should feel distinct and true to their personality
4. Scene atmosphere should permeate every paragraph
5. If this is a DECISION POINT scene, end the prose at the moment of maximum tension —
   stop just before the character makes the crucial choice, leaving the reader breathless
6. No headers, no bullet points, no meta-commentary — pure prose only
7. Maintain therapeutic resonance: conflict opens understanding, not just drama

Do NOT output JSON or any structured data. Write the scene prose directly."""

LENGTH_SPECS = {
    "brief":    ("100-200字", 512),
    "medium":   ("250-450字", 1024),
    "detailed": ("500-900字", 2048),
}


def compose_scene(
    scene_plan: ScenePlan,
    scene_setup: str,
    atmosphere: str,
    character_actions: list[CharacterAction],
    world_config: dict,
    chapter_number: int,
    therapeutic_intention: str = "",
    chapter_length_hint: str = "medium",
    is_decision_point: bool = False,
) -> str:
    """Compose prose for a single scene."""
    log.info(
        "Composing ch%d scene%d '%s' (tension=%.2f, decision=%s)",
        chapter_number,
        scene_plan.scene_number,
        scene_plan.title,
        scene_plan.tension_level,
        is_decision_point,
    )

    word_range, max_tokens = LENGTH_SPECS.get(chapter_length_hint, LENGTH_SPECS["medium"])

    actions_text = ""
    for action in character_actions:
        actions_text += f"\n【{action.character_name}】\n"
        actions_text += f"  行动: {action.public_action}\n"
        actions_text += f"  内心: {action.private_thought}\n"
        if action.dialogue:
            actions_text += f"  台词: \"{action.dialogue}\"\n"
        if action.emotional_state:
            actions_text += f"  情感: {action.emotional_state}\n"
        if action.growth_moment:
            actions_text += f"  成长瞬间: {action.growth_moment}\n"

    decision_note = (
        "\n⚡ 重要: 这是决策点场景。在张力最高峰时戛然而止，"
        "以一个悬而未决的瞬间结束——读者将决定接下来发生什么。"
        "结尾不要解决任何冲突，只是把选择摆在读者面前。"
        if is_decision_point else ""
    )

    user_msg = (
        f"请将以下场景整合为连贯的故事叙述。\n\n"
        f"场景信息:\n"
        f"- 第{chapter_number}章 · 场景{scene_plan.scene_number}:「{scene_plan.title}」\n"
        f"- 场景描述: {scene_plan.description}\n"
        f"- 张力等级: {scene_plan.tension_level:.0%}\n"
        f"- 导演场景设定: {scene_setup}\n"
        f"- 氛围: {atmosphere}\n"
        f"- 治疗意图: {therapeutic_intention}"
        f"{decision_note}\n\n"
        f"世界: {world_config.get('name', '')} — {world_config.get('description', '')[:150]}\n\n"
        f"角色行动:\n{actions_text}\n\n"
        f"请写出这一场景的故事正文（约{word_range}）。\n"
        f"文字要有文学质感，情感层次丰富，叙事流畅自然。\n"
        f"只输出故事正文，不需要任何标题或说明。"
    )

    prose = chat(
        messages=[
            {"role": "system", "content": COMPOSER_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.88,
        max_tokens=max_tokens,
    )

    log.info("Scene %d composed: %d chars", scene_plan.scene_number, len(prose))
    return prose.strip()
