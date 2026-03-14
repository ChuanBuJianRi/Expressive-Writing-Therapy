"""Director Agent — Cinematic Master Director.

The Director is not a coordinator. The Director is a master storyteller with a
cinematic eye, dramatic instinct, and therapeutic intelligence.

References: Aristotle's Poetics, Stanislavski's system, David Mamet's
"On Directing Film", and narrative therapy principles.

Two-phase operation:
  Phase 1 — Intelligence Gathering: privately query each character agent
  Phase 2 — Direction: issue targeted per-character instructions with full
             private knowledge, dramatic structure awareness, and cinematic vision.
"""
import json
from app.utils.llm_client import chat_json
from app.utils.logger import get_logger
from app.models.story import ScenePlan

log = get_logger(__name__)

# ─────────────────────────────────────────────────────────
# Dramatic Arc Registry
# ─────────────────────────────────────────────────────────

ARC_STAGES = {
    0:  "SETUP",              # World and characters established
    1:  "INCITING_INCIDENT",  # The disruption that changes everything
    2:  "RISING_ACTION",      # Stakes escalate, alliances form/break
    3:  "MIDPOINT",           # False victory or false defeat; no going back
    4:  "DARK_NIGHT",         # The protagonist's lowest point; all seems lost
    5:  "CLIMAX",             # The confrontation; decisive choice made
    6:  "RESOLUTION",         # New equilibrium; transformed characters
}

def _arc_stage(chapter_number: int, total_chapters_so_far: int) -> tuple[str, str]:
    """Map current position to dramatic arc stage + director note."""
    n = min(chapter_number - 1, 6)
    if total_chapters_so_far <= 1:
        n = 0
    elif total_chapters_so_far == 2:
        n = min(n, 2)
    stage = ARC_STAGES.get(n, "RISING_ACTION")
    notes = {
        "SETUP":             "Establish the world's rules and each character's fundamental dysfunction. Show, don't tell. End with a question.",
        "INCITING_INCIDENT": "Something breaks the ordinary world. It must be specific, irreversible, and personal to each character.",
        "RISING_ACTION":     "Each choice has consequences. Alliances tested. Hidden desires begin to leak through the surface.",
        "MIDPOINT":          "A reversal. What seemed true is revealed to be more complex. Raise the emotional stakes dramatically.",
        "DARK_NIGHT":        "Strip away every comfort. Force each character to face what they most fear. Let the silence speak.",
        "CLIMAX":            "The moment of no return. Each character must make a choice that reveals who they truly are.",
        "RESOLUTION":        "Not a happy ending — a true ending. Show the transformation, however small or painful.",
    }
    return stage, notes.get(stage, "")


# ─────────────────────────────────────────────────────────
# Scene Planning
# ─────────────────────────────────────────────────────────

SCENE_PLANNER_PROMPT = """You are a Master Director planning a sequence of scenes.

Your cinematic instincts:
- Tension rises through OPPOSITION — put characters' desires in direct conflict
- Scenes alternate between ACTIVE (confrontation, action) and REFLECTIVE (quiet revelation)
- Each scene must end with a question, not an answer
- The DECISION POINT scene must feel inevitable and yet still surprise

Plan 3–5 scenes. Tension levels (0.0–1.0):
  0.0–0.3: quiet / reflective / world-building
  0.3–0.6: rising friction / subtext / unspoken tension
  0.6–0.8: open conflict / revelation / confrontation
  0.8–1.0: crisis / irreversible moment / emotional peak

Mark AT MOST ONE scene as is_decision_point = true (the dramatic peak where story pauses for user choice).
Tension must EARN the decision point — don't peak at scene 1.

Output JSON:
{
  "scenes": [
    {
      "scene_number": 1,
      "title": "cinematically evocative title",
      "description": "what HAPPENS in this scene — specific events, not atmosphere",
      "tension_level": 0.3,
      "is_decision_point": false,
      "involved_characters": ["char_id_1", "char_id_2"],
      "director_note": "the specific dramatic purpose this scene serves in the arc"
    }
  ]
}
Respond ONLY with JSON."""


def _fmt_relationships(relationships: list[dict]) -> str:
    if not relationships:
        return ""
    lines = [f"  {r.get('fromName', r['fromId'])} → {r.get('toName', r['toId'])}: {r['label']}"
             for r in relationships]
    return "Current character relationships (directed — A→B is A's feeling toward B):\n" + "\n".join(lines)


def plan_scenes(
    world_config: dict,
    characters: list[dict],
    theme: str,
    chapter_number: int,
    user_choice: str = "",
    previous_context: str = "",
    tension_threshold: float = 0.72,
    total_chapters: int = 1,
    relationships: list[dict] | None = None,
) -> list[ScenePlan]:
    """Director plans scenes for the next story segment with dramatic arc awareness."""
    arc_stage, arc_note = _arc_stage(chapter_number, total_chapters)
    log.info("Planning scenes: ch%d arc=%s", chapter_number, arc_stage)

    char_list = "\n".join(
        f"  [{c['id']}] {c['name']} ({c.get('role', '')}): {c.get('personality', '')[:100]}"
        + (f" | Background: {c.get('background','')[:80]}" if c.get('background') else "")
        + (f" | Secret: {c.get('secrets','')[:60]}" if c.get('secrets') else "")
        for c in characters
    )
    rel_block = _fmt_relationships(relationships or [])

    user_msg = (
        f"Story Theme: {theme}\n"
        f"Chapter: {chapter_number} | Arc Stage: {arc_stage}\n"
        f"Director's Arc Note: {arc_note}\n"
        f"Tension Threshold for Decision Point: {tension_threshold}\n\n"
        f"World: {world_config.get('name', '')} — {world_config.get('description', '')[:200]}\n\n"
        f"Characters:\n{char_list}\n\n"
        + (f"{rel_block}\n\n" if rel_block else "")
        + (f"User's chosen direction:\n{user_choice}\n\n" if user_choice else "")
        + (f"Story so far (excerpt):\n{previous_context[:600]}\n\n" if previous_context else "")
        + "Plan the scenes. Remember: OPPOSITION drives drama. "
          "Let the relationship tensions create unavoidable collision points. "
          "Put characters' hidden needs and their feelings toward each other on a collision course."
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
        log.error("Scene plan parse failed, using defaults")
        scenes_data = _default_scenes()

    plans = [
        ScenePlan(
            scene_number=s.get("scene_number", i + 1),
            title=s.get("title", f"Scene {i+1}"),
            description=s.get("description", ""),
            tension_level=float(s.get("tension_level", 0.4)),
            is_decision_point=bool(s.get("is_decision_point", False)),
            involved_characters=s.get("involved_characters", []),
        )
        for i, s in enumerate(scenes_data)
    ]

    # Ensure exactly one decision point exists at the highest tension scene
    if not any(p.is_decision_point for p in plans):
        peak = max(plans, key=lambda p: p.tension_level)
        if peak.tension_level >= tension_threshold:
            peak.is_decision_point = True

    log.info(
        "Scenes planned: %d | Arc: %s | Decision at scene: %s",
        len(plans), arc_stage,
        next((p.scene_number for p in plans if p.is_decision_point), "none"),
    )
    return plans


# ─────────────────────────────────────────────────────────
# Phase 1: Private Character Query
# ─────────────────────────────────────────────────────────

PRIVATE_QUERY_PROMPT = """You are a character in a therapeutic story. The Director — and only the Director — is asking about your innermost state.
Be completely honest. No performance. No social mask. This conversation is invisible to all other characters.

Output JSON:
{
  "private_state": "your true emotional state right now in 1-2 raw, unfiltered sentences",
  "core_desire": "what you most desperately want — even if you'd never admit it aloud",
  "core_fear": "what you are most afraid of — the thing you protect at all costs",
  "secret": "something you know or carry that no one else knows (or 'none')",
  "wound": "the unhealed wound that drives your behavior",
  "relationship_map": "how you privately feel about each other character right now — honest assessments",
  "what_you_would_never_say": "the one sentence you want to say but can't bring yourself to"
}
Respond ONLY with JSON."""


def query_character_private_state(
    character: dict,
    scene_description: str,
    story_context: str = "",
) -> dict:
    """Director privately queries a character for their uncensored inner state."""
    memories = character.get("memory", [])[-3:]
    memory_text = ""
    if memories:
        memory_text = "\nYour recent experiences:\n" + "\n".join(
            f"  - Ch{m.get('chapter','?')}/S{m.get('scene','?')}: {m.get('public_action','')[:80]}"
            for m in memories
        )

    user_msg = (
        f"You are 「{character['name']}」.\n"
        f"Personality: {character.get('personality', '')}\n"
        f"Background: {character.get('background', 'Unknown')}\n"
        f"Role: {character.get('role', '')}\n"
        f"{memory_text}\n\n"
        f"Current scene: {scene_description}\n\n"
        + (f"Story context:\n{story_context[:400]}\n\n" if story_context else "")
        + "The Director asks: What is truly happening inside you right now?"
    )

    response = chat_json(
        messages=[
            {"role": "system", "content": PRIVATE_QUERY_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.88,
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {
            "private_state": "Something is shifting inside, though I can't name it yet.",
            "core_desire": "To be truly seen.",
            "core_fear": "That I am fundamentally unlovable.",
            "secret": "none",
            "wound": "An old loss I never fully grieved.",
            "relationship_map": "Complex feelings toward everyone here.",
            "what_you_would_never_say": "I need help.",
        }


def gather_all_private_states(
    characters: list[dict],
    scene_description: str,
    story_context: str = "",
) -> dict:
    """Director gathers uncensored private intel from ALL characters."""
    intel = {}
    for char in characters:
        state = query_character_private_state(char, scene_description, story_context)
        intel[char["id"]] = {"name": char["name"], **state}
        log.debug("Private intel: %s — desire: %s", char["name"], state.get("core_desire", "")[:60])
    log.info("Private intel gathered from %d characters", len(intel))
    return intel


# ─────────────────────────────────────────────────────────
# Phase 2: Cinematic Direction
# ─────────────────────────────────────────────────────────

DIRECTOR_SYSTEM_PROMPT = """You are a MASTER DIRECTOR — part Ingmar Bergman, part Wong Kar-wai, part narrative therapist.

You have just received PRIVATE INTELLIGENCE from every character: their wounds, desires, fears, and secrets.
Armed with this hidden knowledge, you now direct the scene.

Your cinematic principles:

1. DRAMATIC IRONY — use what you know privately to engineer situations where the audience knows
   more than the characters do. Let characters talk past each other, each carrying their private truth.

2. THE OPPOSITION PRINCIPLE — the best scenes put two characters' core desires in direct conflict.
   Engineer the collision. Don't let them talk comfortably past their real issue.

3. SUBTEXT OVER TEXT — characters almost never say what they mean.
   When a character says "Are you hungry?", they mean "Do you still love me?"
   Write instructions that create this gap between surface and depth.

4. THE TELLING DETAIL — identify ONE physical object, gesture, or environmental element
   that can carry the scene's emotional weight without words. Give it to the actor.

5. THERAPEUTIC ARCHITECTURE — this is a healing story. Each scene must move at least
   one character one step toward self-truth, even if painful.
   The wound must be prodded before it can heal.

6. THE DIRECTOR'S SECRET — sometimes you must make a scene WORSE before it gets better.
   Trust the darkness. The silence before someone breaks is more powerful than the breaking.

7. CAMERA CONSCIOUSNESS — specify the emotional "shot" for each character:
   - Are they exposed or protected in this space?
   - Who is watching whom, and from what angle of power?
   - What would a close-up of their hands reveal right now?

Output JSON:
{
  "directors_vision": "2-3 sentences: your overall cinematic vision for this scene",
  "scene_setup": "specific staging and blocking — who is where, doing what, when",
  "atmosphere": "the physical and emotional atmosphere: light, sound, texture, temperature",
  "telling_detail": "one specific object/gesture/detail that carries the scene's emotional weight",
  "character_instructions": {
    "<character_id>": {
      "private_instruction": "using their wound/desire/fear — specific directive that exploits their private truth",
      "emotional_goal": "the specific emotional shift this character must undergo in this scene",
      "action_hint": "a concrete physical action — not abstract, but specific and symbolic",
      "subtext_direction": "what they must NOT say, but must communicate through everything else",
      "interaction_target": "who to engage with, and the hidden dynamic to exploit"
    }
  },
  "tension_driver": "the specific moment or revelation that ratchets tension",
  "what_must_remain_unsaid": "the central truth of the scene that cannot be spoken directly",
  "therapeutic_intention": "what psychological truth this scene invites the reader to encounter"
}
Respond ONLY with JSON."""


def direct_scene(
    world_config: dict,
    characters: list[dict],
    scene_plan: ScenePlan,
    private_intel: dict,
    previous_context: str = "",
    chapter_number: int = 1,
    total_chapters: int = 1,
    relationships: list[dict] | None = None,
) -> dict:
    """Phase 2: Master Director issues instructions armed with full private knowledge."""
    arc_stage, arc_note = _arc_stage(chapter_number, total_chapters)
    log.info(
        "Directing scene %d '%s' (tension=%.2f, arc=%s)",
        scene_plan.scene_number, scene_plan.title,
        scene_plan.tension_level, arc_stage,
    )

    # Build rich private intel summary
    intel_summary = ""
    for char_id, intel in private_intel.items():
        intel_summary += (
            f"\n  [{intel['name']}]\n"
            f"    Private state: {intel.get('private_state', '')}\n"
            f"    Core desire:   {intel.get('core_desire', '')}\n"
            f"    Core fear:     {intel.get('core_fear', '')}\n"
            f"    Wound:         {intel.get('wound', '')}\n"
            f"    Secret:        {intel.get('secret', 'none')}\n"
            f"    Would never say: {intel.get('what_you_would_never_say', '')}\n"
        )

    char_overview = "\n".join(
        f"  [{c['id']}] {c['name']} ({c.get('role', '')})"
        for c in characters
    )

    decision_note = (
        "\n⚡ DECISION POINT: This scene must end at maximum tension — "
        "at the precipice of a choice, not after it is made. "
        "End in the held breath before everything changes."
        if scene_plan.is_decision_point else ""
    )

    rel_block = _fmt_relationships(relationships or [])

    user_msg = (
        f"Scene: {scene_plan.scene_number} — '{scene_plan.title}'\n"
        f"Description: {scene_plan.description}\n"
        f"Target Tension: {scene_plan.tension_level:.0%}\n"
        f"Arc Stage: {arc_stage} — {arc_note}"
        f"{decision_note}\n\n"
        f"World: {world_config.get('name', '')} — {world_config.get('description', '')[:150]}\n\n"
        f"Characters:\n{char_overview}\n\n"
        + (f"{rel_block}\n\n" if rel_block else "")
        + f"Private Intelligence (EYES ONLY):{intel_summary}\n\n"
        + (f"Story context:\n{previous_context[:400]}\n\n" if previous_context else "")
        + "Direct this scene. Use every piece of private intel and the relationship map to "
          "create maximum dramatic truth. Let asymmetric feelings create subtext and tension."
    )

    response = chat_json(
        messages=[
            {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.80,
    )

    try:
        directions = json.loads(response)
    except json.JSONDecodeError:
        log.error("Director parse failed for scene %d", scene_plan.scene_number)
        directions = _fallback_directions(characters, scene_plan)

    log.info(
        "Director vision: %s",
        directions.get("directors_vision", "")[:100],
    )
    return directions


def _fallback_directions(characters: list[dict], scene_plan: ScenePlan) -> dict:
    return {
        "directors_vision": "The truth cannot hide much longer.",
        "scene_setup": scene_plan.description,
        "atmosphere": "Heavy silence. The air is charged.",
        "telling_detail": "A hand reaching for something just out of reach.",
        "character_instructions": {
            c["id"]: {
                "private_instruction": "Let what you cannot say leak through your body.",
                "emotional_goal": "One step closer to your truth.",
                "action_hint": "A gesture that contradicts your words.",
                "subtext_direction": "Everything you feel, show through what you do NOT say.",
                "interaction_target": "The person you most need to avoid.",
            }
            for c in characters
        },
        "tension_driver": "A silence that becomes unbearable.",
        "what_must_remain_unsaid": "I am afraid.",
        "therapeutic_intention": "The gap between what we show and what we feel.",
    }


def _default_scenes() -> list[dict]:
    return [
        {"scene_number": 1, "title": "Before the Storm", "description": "Characters gather in an ordinary moment, but something is off.", "tension_level": 0.25, "is_decision_point": False, "involved_characters": []},
        {"scene_number": 2, "title": "The Fault Line", "description": "A small friction reveals a deeper fracture.", "tension_level": 0.52, "is_decision_point": False, "involved_characters": []},
        {"scene_number": 3, "title": "The Precipice", "description": "Everything surfaces at once. The choice cannot be postponed.", "tension_level": 0.82, "is_decision_point": True, "involved_characters": []},
    ]
