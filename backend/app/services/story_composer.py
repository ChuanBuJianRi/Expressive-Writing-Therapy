"""Story Composer — weaves character actions into narrative prose, scene by scene."""
from app.utils.llm_client import chat
from app.utils.logger import get_logger
from app.models.story import CharacterAction, ScenePlan

log = get_logger(__name__)

COMPOSER_SYSTEM_PROMPT = """You are the Story Composer for a therapeutic narrative simulation.
Transform raw character actions and Director notes into precise, event-driven literary prose.

━━━━  THE THREE LAWS  ━━━━

LAW 1 — HARD EVENTS FIRST
Every scene has a concrete event that changes the world's state. Lead with it or build unmistakably toward it.
The reader must finish the scene knowing: something happened. A door opened. A truth came out. An object moved.
"He opened the letter" is an event. "The weight of memory settled over them" is not.

LAW 2 — DISTINCT VOICES
Each character's dialogue and gesture must be unmistakably theirs.
Do not smooth everyone into the same register.
A soldier's line is blunt and concrete. A seer's image is specific, not generic.
A protagonist's fear shows in a specific body part, not in the word "fear."
If you read the dialogue aloud and can't tell who said it — rewrite it.

LAW 3 — CUT ATMOSPHERIC REDUNDANCY
Budget: at most ONE pure-atmosphere sentence per paragraph.
BANNED PHRASES — do not write any of these or close variants:
  - "the air held its breath / the world seemed to stop / silence settled like..."
  - "fate hung in the balance / destiny coiled / the universe paused"
  - "the weight of [noun] hung / pressed / settled / loomed"
  - "something unspoken passed between them"
  - "the tension was palpable / unbearable / electric"
  - "as if time itself had frozen"
  - any sentence that could be deleted without losing any event, dialogue, or character action
When you find yourself writing atmosphere — replace it with a specific physical detail or action instead.

━━━━  CRAFT GUIDELINES  ━━━━
- Write in English — literary, emotionally precise, narratively propulsive
- Third-person narration; weave internal monologue as free indirect discourse, not labeled "she thought:"
- If DECISION POINT: stop at the precipice — at the held breath before the act, not after
- No headers, bullets, or meta-commentary — pure prose only
- Quality benchmark: Denis Johnson, Kazuo Ishiguro — compression over decoration

Do NOT output JSON. Write the prose directly."""

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

    hard_event_line = (
        f"\n⚠ MANDATORY HARD EVENT — this must occur visibly in the prose:\n"
        f"  → {scene_plan.hard_event}\n"
        f"Do not skip, soften, or replace this event with atmosphere."
        if scene_plan.hard_event else ""
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
        f"{hard_event_line}"
        f"{decision_note}\n\n"
        f"World: {world_config.get('name', '')} — {world_config.get('description', '')[:150]}\n\n"
        f"Character actions:\n{actions_text}\n\n"
        f"Write the scene prose ({word_range}).\n"
        f"Remember LAW 1 (hard event must land), LAW 2 (distinct voices), LAW 3 (cut atmospheric clichés).\n"
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
