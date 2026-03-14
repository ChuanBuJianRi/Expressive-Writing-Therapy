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
Respond ONLY with the JSON. Write in English."""


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

    user_msg = (
        f"You are \"{character['name']}\". {char_intro}\n"
        f"Personality: {character['personality']}\n"
        f"Background: {character.get('background', 'Unknown')}\n"
        f"Role: {character.get('role', 'Character')}\n\n"
        f"Current scene: {scene_setting}\n"
        f"Scene tension: {scene_tension:.0%}\n\n"
        f"Private Director's instructions (only you know these):\n"
        f"- Core directive: {director_instruction.get('private_instruction', 'Follow your instincts')}\n"
        f"- Emotional goal: {director_instruction.get('emotional_goal', 'Express your authentic self')}\n"
        f"- Action hint: {director_instruction.get('action_hint', 'React naturally')}\n"
        f"- Interaction target: {director_instruction.get('interaction_target', 'Those around you')}\n\n"
        + (f"Other characters' visible actions:{others_ctx}\n\n" if others_ctx else "You act first in this scene.\n\n")
        + (f"Your memories from earlier:{memory_ctx}\n\n" if memory_ctx else "")
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
