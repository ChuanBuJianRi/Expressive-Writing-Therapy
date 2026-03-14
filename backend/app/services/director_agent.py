"""Director Agent — the orchestrator that issues instructions to character agents."""
import json
from app.utils.llm_client import chat_json
from app.utils.logger import get_logger

log = get_logger(__name__)

DIRECTOR_SYSTEM_PROMPT = """You are the Director Agent of a therapeutic story simulation system.
Your role is to orchestrate the story by issuing private instructions to each character agent.

You have access to:
- The world setting and rules
- The chapter plan (outline, conflict level, despair level)
- All characters' previous public actions and private thoughts
- The overall story arc

Your job is to:
1. Decide what plot events happen in this chapter
2. Issue PRIVATE instructions to each character (they can't see each other's instructions)
3. Control the pacing — manage conflict and emotional tension according to the chapter plan
4. Ensure therapeutic value — the story should facilitate psychological exploration and healing
5. Create meaningful character interactions that reveal each character's inner world

Output a JSON object:
{
  "chapter_events": "描述这一章的主要事件和情境",
  "scene_setting": "场景描写，为角色提供环境氛围",
  "character_instructions": {
    "<character_id>": {
      "private_instruction": "给这个角色的私密指令，其他角色看不到",
      "emotional_goal": "这个角色在本章应该经历的情感变化",
      "interaction_hints": "建议与哪些角色互动，以什么方式"
    }
  },
  "conflict_trigger": "本章的冲突触发点（如有）",
  "therapeutic_intention": "本章的治疗意图——希望读者从中获得什么"
}

Respond ONLY with the JSON object."""


def direct_chapter(
    world_config: dict,
    characters: list[dict],
    chapter_plan: dict,
    previous_chapters: list[dict] = None,
    user_input: str = "",
) -> dict:
    """Issue per-character instructions for a chapter (LLM Call #3)."""
    log.info(
        "Director planning chapter %d: %s",
        chapter_plan.get("chapter_number", 0),
        chapter_plan.get("title", ""),
    )

    char_summaries = []
    for c in characters:
        summary = f"[{c['id']}] {c['name']} ({c.get('role', '')}): {c['personality']}"
        if c.get("memory"):
            last_action = c["memory"][-1] if c["memory"] else {}
            summary += f"\n  上一章行为: {last_action.get('public_action', 'N/A')}"
            summary += f"\n  上一章内心: {last_action.get('private_thought', 'N/A')}"
        char_summaries.append(summary)

    prev_summary = ""
    if previous_chapters:
        for ch in previous_chapters[-2:]:  # last 2 chapters for context
            prev_summary += f"\n--- 第{ch.get('chapter_number', '?')}章 ---\n"
            prev_summary += ch.get("prose", "")[:500] + "\n"

    user_msg = f"""世界设定:
{json.dumps(world_config, ensure_ascii=False, indent=2)}

本章计划:
- 章节: 第{chapter_plan['chapter_number']}章 「{chapter_plan['title']}」
- 大纲: {chapter_plan['summary']}
- 冲突强度: {chapter_plan.get('conflict_level', 0.5)}
- 绝望程度: {chapter_plan.get('despair_level', 0.3)}
- 关键事件: {', '.join(chapter_plan.get('key_events', []))}

角色信息:
{chr(10).join(char_summaries)}

{f"前情回顾:{prev_summary}" if prev_summary else "这是故事的开篇。"}

{f"用户额外指示: {user_input}" if user_input else ""}

请为每个角色发出私密指令。"""

    response = chat_json(
        messages=[
            {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.8,
    )

    try:
        directions = json.loads(response)
    except json.JSONDecodeError:
        log.error("Failed to parse director output, using fallback")
        directions = {
            "chapter_events": chapter_plan.get("summary", "故事继续..."),
            "scene_setting": "角色们在这个世界中继续他们的旅程。",
            "character_instructions": {
                c["id"]: {
                    "private_instruction": f"继续探索你的内心世界，与其他角色互动。",
                    "emotional_goal": "展现真实的自我。",
                    "interaction_hints": "与身边的人交流。",
                }
                for c in characters
            },
            "conflict_trigger": "一个意想不到的相遇。",
            "therapeutic_intention": "帮助读者看到不同视角下的同一个世界。",
        }

    log.info("Director issued instructions for %d characters",
             len(directions.get("character_instructions", {})))
    return directions
