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
      "title": "Chapter title in English",
      "summary": "Chapter outline — key events and emotional arc",
      "conflict_level": 0.3,
      "despair_level": 0.2,
      "key_events": ["Event 1", "Event 2"]
    }
  ]
}

conflict_level and despair_level are floats from 0.0 to 1.0 representing intensity.
Respond ONLY with the JSON object."""

EXTEND_CHAPTER_PROMPT = """You are a Chapter Planner for a therapeutic story simulation system.
The user has chosen a specific direction for the story to continue.

Based on the story so far and the user's choice, plan ONE new chapter that continues in that direction.

Output a JSON object for a SINGLE chapter:
{
  "chapter_number": <next number>,
  "title": "Chapter title reflecting the user's chosen direction",
  "summary": "Chapter outline closely following the user's choice",
  "conflict_level": <float 0.0-1.0>,
  "despair_level": <float 0.0-1.0>,
  "key_events": ["Event 1", "Event 2", "Event 3"]
}

Respond ONLY with the JSON object."""


def plan_chapters(
    world_config: dict,
    characters: list[dict],
    num_chapters: int = 3,
    theme: str = "",
    chapter_length_hint: str = "",
) -> list[ChapterPlan]:
    """Plan the chapter structure for the story (LLM Call #2)."""
    log.info("Planning %d chapters for theme: %s", num_chapters, theme)

    char_summaries = [
        f"- {c['name']} ({c.get('role', 'unknown')}): {c['personality']}"
        for c in characters
    ]

    hint_line = f"\nChapter length preference: {chapter_length_hint}" if chapter_length_hint else ""

    user_msg = (
        f"Story theme: {theme}\n"
        f"Number of chapters: {num_chapters}"
        f"{hint_line}\n\n"
        f"World configuration:\n{json.dumps(world_config, ensure_ascii=False, indent=2)}\n\n"
        f"Characters:\n{chr(10).join(char_summaries)}\n\n"
        f"Plan the story arc for {num_chapters} chapters."
    )

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
        chapters_data = _default_plans(num_chapters)

    plans = _build_plans(chapters_data)
    log.info("Planned %d chapters", len(plans))
    return plans


def extend_story(
    world_config: dict,
    characters: list[dict],
    previous_chapters: list[dict],
    user_choice: str,
    theme: str,
    next_chapter_number: int,
) -> ChapterPlan:
    """Dynamically extend the story by one chapter based on user's branch choice."""
    log.info(
        "Extending story to chapter %d based on choice: %.60s…",
        next_chapter_number,
        user_choice,
    )

    char_summaries = [
        f"- {c['name']} ({c.get('role', 'unknown')}): {c['personality']}"
        for c in characters
    ]

    prev_prose = ""
    for ch in previous_chapters[-2:]:
        prev_prose += f"\n--- Chapter {ch.get('chapter_number', '?')} ---\n"
        prev_prose += ch.get("prose", "")[:400] + "\n"

    user_msg = (
        f"Story theme: {theme}\n"
        f"Next chapter: {next_chapter_number}\n\n"
        f"User's chosen direction:\n{user_choice}\n\n"
        f"World: {world_config.get('name', '')} — {world_config.get('description', '')}\n\n"
        f"Characters:\n{chr(10).join(char_summaries)}\n\n"
        f"Previous story:\n{prev_prose}\n\n"
        f"Plan chapter {next_chapter_number} based on the user's choice."
    )

    _fallback_data = {
        "chapter_number": next_chapter_number,
        "title": f"Chapter {next_chapter_number}",
        "summary": user_choice[:200],
        "conflict_level": 0.5,
        "despair_level": 0.3,
        "key_events": ["The story unfolds", "Characters face the consequences of their choice"],
    }
    try:
        response = chat_json(
            messages=[
                {"role": "system", "content": EXTEND_CHAPTER_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.8,
        )
        data = json.loads(response)
        data.setdefault("chapter_number", next_chapter_number)
    except Exception as e:
        log.error("extend_story failed: %s — using fallback plan", e)
        data = _fallback_data

    plan = ChapterPlan(
        chapter_number=data["chapter_number"],
        title=data.get("title", f"Chapter {next_chapter_number}"),
        summary=data.get("summary", user_choice[:200]),
        conflict_level=data.get("conflict_level", 0.5),
        despair_level=data.get("despair_level", 0.3),
        key_events=data.get("key_events", []),
    )
    log.info("Extended story: chapter %d — %s", plan.chapter_number, plan.title)
    return plan


def _default_plans(num_chapters: int) -> list[dict]:
    return [
        {
            "chapter_number": i + 1,
            "title": f"Chapter {i + 1}",
            "summary": "The story continues to unfold…",
            "conflict_level": min(0.3 + i * 0.2, 0.9),
            "despair_level": min(0.2 + i * 0.1, 0.7),
            "key_events": ["Character interaction", "Emotional development"],
        }
        for i in range(num_chapters)
    ]


def _build_plans(chapters_data: list[dict]) -> list[ChapterPlan]:
    return [
        ChapterPlan(
            chapter_number=ch["chapter_number"],
            title=ch.get("title", f"Chapter {ch['chapter_number']}"),
            summary=ch.get("summary", ""),
            conflict_level=ch.get("conflict_level", 0.5),
            despair_level=ch.get("despair_level", 0.3),
            key_events=ch.get("key_events", []),
        )
        for ch in chapters_data
    ]
