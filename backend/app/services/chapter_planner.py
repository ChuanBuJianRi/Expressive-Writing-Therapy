"""Chapter Planner — plans chapter structure, pacing, and conflict arcs."""
import json
from app.utils.llm_client import chat_json
from app.utils.logger import get_logger
from app.models.story import ChapterPlan

log = get_logger(__name__)

CHAPTER_PLANNER_PROMPT = """You are a Chapter Planner for a therapeutic story simulation system.
Given a world configuration and characters, plan a multi-chapter story arc.

The story arc should follow therapeutic narrative principles:
1. Gradual emotional escalation — start gentle, build to a turning point
2. Each character should have moments of vulnerability and growth
3. Conflict should drive self-discovery, not destruction
4. The final chapter should offer resolution and catharsis (not necessarily a happy ending, but meaningful)

Output a JSON object:
{
  "total_chapters": <number>,
  "chapters": [
    {
      "chapter_number": 1,
      "title": "章节标题",
      "summary": "这一章的大纲，关键事件和情感走向",
      "conflict_level": 0.3,
      "despair_level": 0.2,
      "key_events": ["事件1", "事件2"]
    }
  ]
}

conflict_level and despair_level are floats from 0.0 to 1.0 representing intensity.
Respond ONLY with the JSON object."""


def plan_chapters(
    world_config: dict,
    characters: list[dict],
    num_chapters: int = 3,
    theme: str = "",
) -> list[ChapterPlan]:
    """Plan the chapter structure for the story (LLM Call #2)."""
    log.info("Planning %d chapters for theme: %s", num_chapters, theme)

    char_summaries = []
    for c in characters:
        char_summaries.append(
            f"- {c['name']} ({c.get('role', 'unknown')}): {c['personality']}"
        )

    user_msg = f"""故事主题: {theme}
章节数量: {num_chapters}

世界设定:
{json.dumps(world_config, ensure_ascii=False, indent=2)}

角色列表:
{chr(10).join(char_summaries)}

请规划 {num_chapters} 个章节的故事大纲。"""

    response = chat_json(
        messages=[
            {"role": "system", "content": CHAPTER_PLANNER_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.7,
    )

    try:
        data = json.loads(response)
        chapters_data = data.get("chapters", [])
    except json.JSONDecodeError:
        log.error("Failed to parse chapter plan JSON, using defaults")
        chapters_data = [
            {
                "chapter_number": i + 1,
                "title": f"第{i + 1}章",
                "summary": "故事继续展开...",
                "conflict_level": 0.3 + i * 0.2,
                "despair_level": 0.2 + i * 0.1,
                "key_events": ["角色互动", "情感发展"],
            }
            for i in range(num_chapters)
        ]

    plans = []
    for ch in chapters_data:
        plans.append(
            ChapterPlan(
                chapter_number=ch["chapter_number"],
                title=ch["title"],
                summary=ch["summary"],
                conflict_level=ch.get("conflict_level", 0.5),
                despair_level=ch.get("despair_level", 0.3),
                key_events=ch.get("key_events", []),
            )
        )

    log.info("Planned %d chapters", len(plans))
    return plans
