"""Story Composer — weaves character actions into narrative prose, scene by scene."""
from app.utils.llm_client import chat
from app.utils.logger import get_logger
from app.models.story import CharacterAction, ScenePlan

log = get_logger(__name__)

COMPOSER_SYSTEM_PROMPT = """You are the Story Composer for a therapeutic narrative simulation.
Transform raw character actions and Director notes into beautiful literary prose.

Writing guidelines:
1. Write in English — literary, evocative, and emotionally precise
2. Third-person narration; weave internal monologue subtly into the flow
3. Each character's actions, gestures, and words should feel distinct and true to their personality
4. Scene atmosphere should permeate every paragraph — light, texture, sound, silence
5. If this is a DECISION POINT scene, end the prose at the moment of maximum tension —
   stop just before the character makes the crucial choice, leaving the reader breathless
6. No headers, no bullet points, no meta-commentary — pure prose paragraphs only
7. Maintain therapeutic resonance: conflict opens understanding, not just drama
8. Quality benchmark: contemporary literary fiction — think Kazuo Ishiguro, Celeste Ng

Do NOT output JSON or any structured data. Write the scene prose directly."""

LENGTH_SPECS = {
    "brief":    ("100-200 words", 512),
    "medium":   ("250-450 words", 1024),
    "detailed": ("500-900 words", 2048),
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
        actions_text += f"\n[{action.character_name}]\n"
        actions_text += f"  Action:  {action.public_action}\n"
        actions_text += f"  Thought: {action.private_thought}\n"
        if action.dialogue:
            actions_text += f"  Dialogue: \"{action.dialogue}\"\n"
        if action.emotional_state:
            actions_text += f"  Emotion: {action.emotional_state}\n"
        if action.growth_moment:
            actions_text += f"  Growth: {action.growth_moment}\n"

    decision_note = (
        "\n⚡ IMPORTANT: This is a DECISION POINT scene. "
        "End the prose at the peak of tension — stop at the precipice, not after the leap. "
        "Do not resolve the conflict. Leave the reader holding their breath, "
        "poised at the moment just before everything changes."
        if is_decision_point else ""
    )

    user_msg = (
        f"Compose a cohesive scene narrative from the following material.\n\n"
        f"Scene information:\n"
        f"- Chapter {chapter_number} · Scene {scene_plan.scene_number}: \"{scene_plan.title}\"\n"
        f"- Scene description: {scene_plan.description}\n"
        f"- Tension level: {scene_plan.tension_level:.0%}\n"
        f"- Director's staging: {scene_setup}\n"
        f"- Atmosphere: {atmosphere}\n"
        f"- Therapeutic intention: {therapeutic_intention}"
        f"{decision_note}\n\n"
        f"World: {world_config.get('name', '')} — {world_config.get('description', '')[:150]}\n\n"
        f"Character actions:\n{actions_text}\n\n"
        f"Write the scene prose ({word_range}).\n"
        f"Make it literary, emotionally layered, and narratively fluid.\n"
        f"Output only the scene prose — no titles, no headings, no commentary."
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
