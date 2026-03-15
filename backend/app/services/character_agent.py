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

━━━━  THE VOICE RULE  ━━━━
Your speech and actions must be UNMISTAKABLY YOURS — no two characters should sound alike.
Match your voice to your character type:

  SOLDIER / RANGER / FIGHTER type:
    - Short declarative sentences. Concrete nouns, not abstractions.
    - "There's someone behind the east wall." Not "I sense a presence of unease."
    - Dialogue is sparse, direct, often a warning or a judgment. Almost no metaphor.
    - Action over reflection. When uncertain, checks exits, not feelings.

  SEER / ORACLE / MYSTIC type:
    - Poetic, BUT grounded in a specific image — not generic prophecy.
    - One striking image per exchange. NOT every line.
    - Asks questions more than makes statements. Silence is part of their speech.
    - "The candle didn't flicker when you walked in." Not "Fate coils around you."

  PROTAGONIST / YOUNG HERO / UNCERTAIN type:
    - Contradicts themselves. Starts sentences and stops. Changes their mind mid-action.
    - Real fear shows as specific physical sensation: hands, throat, chest.
    - Impulsive micro-actions before thinking: reaches for something, then pulls back.
    - Dialogue has filler, hesitation, correction: "I didn't— I mean, I thought—"

  OTHER / ANTAGONIST / AUTHORITY type:
    - Controlled surface, specific tells that reveal cracks.
    - Economy of words. Every word chosen. No excess.

━━━━  HARD EVENT RULE  ━━━━
Your action must connect to the scene's concrete event — do something specific that advances or responds to
what is actually happening, not just react emotionally to atmosphere.

Rules:
1. Stay completely in character — your personality and background define every choice
2. Private Director instructions are yours alone — honor them through ACTION, not exposition
3. Show, don't tell: convey inner states through gesture, object, and specific action
4. Your dialogue must sound like YOU, not like a narrator paraphrasing your feelings

Output JSON:
{
  "public_action": "SHORT action/gesture, max 6-8 words — e.g. 'leans against the wall, arms crossed' or 'slides the letter across the table'",
  "private_thought": "inner monologue in YOUR voice — not the narrator's, not generic",
  "dialogue": "exact words in YOUR voice (empty string if silent — silence is a valid choice)",
  "emotional_state": "one or two keywords, e.g. 'tense' or 'quietly furious'",
  "growth_moment": "if something shifts in your understanding, name it in a few words; else empty"
}
Respond ONLY with the JSON. Write in English."""


def generate_character_action(
    character: dict,
    world_config: dict,
    director_instruction: dict,
    scene_setting: str,
    other_characters_public: list[dict] = None,
    scene_tension: float = 0.5,
    round_number: int = 1,
    total_rounds: int = 1,
) -> CharacterAction:
    """Generate a character's public action for a scene (Director Phase 2 output)."""
    log.info("Character '%s' acting in scene (tension=%.2f)", character["name"], scene_tension)

    others_ctx = ""
    if other_characters_public:
        for other in other_characters_public:
            others_ctx += f"\n- {other['name']}: {other.get('public_action', '(has not acted yet)')}"
            if other.get("dialogue"):
                others_ctx += f'\n  Said: "{other["dialogue"]}"'

    memory_ctx = ""
    if character.get("memory"):
        for mem in character["memory"][-3:]:
            memory_ctx += f"\n- Chapter {mem.get('chapter', '?')}: {mem.get('public_action', '')[:80]}"

    is_new = character.get("is_story_character", False)
    char_intro = (
        "(You are a newly introduced character — this is your first appearance. Make a vivid, lasting impression on the reader.)"
        if is_new else ""
    )

    secrets_line = (
        f"Secrets (known only to you): {character['secrets']}\n"
        if character.get("secrets") else ""
    )

    user_msg = (
        f"You are \"{character['name']}\". {char_intro}\n"
        f"Personality: {character['personality']}\n"
        f"Background: {character.get('background', 'Unknown')}\n"
        f"{secrets_line}"
        f"Role: {character.get('role', 'Character')}\n\n"
        f"YOUR VOICE MANDATE — every word you speak and every action you take must be consistent with your personality above.\n"
        f"Do NOT sound like other characters. Do NOT sound like a narrator. Sound like YOU.\n"
        f"Derive your speech rhythm, vocabulary, and emotional register directly from your personality description.\n\n"
        f"Current scene: {scene_setting}\n"
        f"Scene tension: {scene_tension:.0%}\n\n"
        f"Private Director's instructions (only you know these):\n"
        f"- Core directive: {director_instruction.get('private_instruction', 'Follow your instincts')}\n"
        f"- Emotional goal: {director_instruction.get('emotional_goal', 'Express your authentic self')}\n"
        f"- Action hint: {director_instruction.get('action_hint', 'React naturally')}\n"
        f"- Interaction target: {director_instruction.get('interaction_target', 'Those around you')}\n\n"
        + (f"Other characters' visible actions:{others_ctx}\n\n" if others_ctx else "You act first in this scene.\n\n")
        + (f"Your memories from earlier:{memory_ctx}\n\n" if memory_ctx else "")
        + (f"This is exchange {round_number} of {total_rounds} in this scene. "
           "React specifically to what others just said or did. Advance the conversation — "
           "don't repeat yourself, build on the tension. Keep your dialogue natural and responsive.\n\n"
           if round_number > 1 else "")
        + "Respond as your character to the current scene."
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
            "public_action": f"{character['name']} stands quietly, observing everything around them.",
            "private_thought": "I need a moment to understand what is happening here.",
            "dialogue": "",
            "emotional_state": "guarded",
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
