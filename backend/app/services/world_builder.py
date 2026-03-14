"""World Builder service — generates structured world configuration from user input."""
import json
from app.utils.llm_client import chat_json
from app.utils.logger import get_logger

log = get_logger(__name__)

WORLD_BUILDER_PROMPT = """You are a World Builder for a therapeutic story simulation system.
Given the user's theme, setting preferences, and genre tags, generate a detailed world configuration.

The world should be:
1. Rich enough to support multi-chapter stories
2. Emotionally resonant — designed to facilitate psychological exploration
3. Safe — no gratuitous violence or traumatic triggers without therapeutic purpose

Output a JSON object with this structure:
{
  "name": "World name",
  "description": "A vivid description of this world in 2-3 sentences",
  "setting": {
    "time_period": "Time period / era",
    "atmosphere": "Atmosphere keywords",
    "key_locations": ["Location 1", "Location 2", "Location 3", "Location 4"],
    "rules": "The core rules or logic of this world",
    "therapeutic_elements": "How this world facilitates psychological healing"
  },
  "tags": ["tag1", "tag2"]
}

Respond ONLY with the JSON object, no additional text."""


def build_world(theme: str, tags: list[str] = None, custom_setting: str = "") -> dict:
    """Generate a world configuration from user input (LLM Call #1)."""
    log.info("Building world for theme: %s", theme)

    user_msg = f"Theme: {theme}\n"
    if tags:
        user_msg += f"Style tags: {', '.join(tags)}\n"
    if custom_setting:
        user_msg += f"Custom setting notes: {custom_setting}\n"

    response = chat_json(
        messages=[
            {"role": "system", "content": WORLD_BUILDER_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.8,
    )

    try:
        world_config = json.loads(response)
    except json.JSONDecodeError:
        log.error("Failed to parse world config JSON: %s", response[:200])
        world_config = {
            "name": theme,
            "description": response[:500],
            "setting": {
                "time_period": "contemporary",
                "atmosphere": "reflective",
                "key_locations": ["The Beginning", "The Journey", "The Turning Point", "The Return"],
                "rules": "The world shifts with the inner lives of those who inhabit it.",
                "therapeutic_elements": "Through narrative, characters explore and transform their inner world.",
            },
            "tags": tags or ["healing"],
        }

    log.info("World built: %s", world_config.get("name", "unknown"))
    return world_config
