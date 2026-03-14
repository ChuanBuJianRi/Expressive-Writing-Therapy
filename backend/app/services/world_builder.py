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
  "name": "世界名称",
  "name_en": "World Name in English",
  "description": "一段描述这个世界的文字",
  "setting": {
    "time_period": "时间设定",
    "atmosphere": "氛围关键词",
    "key_locations": ["地点1", "地点2", "地点3", "地点4"],
    "rules": "这个世界的核心规则或逻辑",
    "therapeutic_elements": "这个世界如何促进心理治愈"
  },
  "tags": ["标签1", "标签2"]
}

Respond ONLY with the JSON object, no additional text."""


def build_world(theme: str, tags: list[str] = None, custom_setting: str = "") -> dict:
    """Generate a world configuration from user input (LLM Call #1)."""
    log.info("Building world for theme: %s", theme)

    user_msg = f"主题: {theme}\n"
    if tags:
        user_msg += f"风格标签: {', '.join(tags)}\n"
    if custom_setting:
        user_msg += f"自定义设定: {custom_setting}\n"

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
            "name_en": theme,
            "description": response[:500],
            "setting": {
                "time_period": "contemporary",
                "atmosphere": "reflective",
                "key_locations": ["起点", "旅途", "目的地", "归处"],
                "rules": "故事随角色的内心变化而展开。",
                "therapeutic_elements": "通过叙事探索内心世界。",
            },
            "tags": tags or ["治愈"],
        }

    log.info("World built: %s", world_config.get("name", "unknown"))
    return world_config
