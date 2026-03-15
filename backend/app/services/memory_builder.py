"""Memory Builder service — generates warm childhood memory scenes for therapeutic recall."""
import json
from app.utils.llm_client import chat, chat_json
from app.utils.logger import get_logger

log = get_logger(__name__)


MEMORY_WORLD_PROMPT = """You are a gentle memory guide who helps people revisit the warm, joyful moments of their childhood.
Using the personal details the user has shared, create a vivid childhood memory world.

Output the following JSON:
{
  "world_name": "A poetic name for the user's childhood place (e.g. 'Sunlit Summers · Maple Street · 1990s')",
  "description": "A warm, sensory-rich description of this childhood world (2–3 sentences)",
  "opening_scene": "An opening scene (~150 words) written in second person ('you'), depicting a specific childhood moment. Rich with sensory detail — the angle of sunlight, familiar smells, distant sounds. Warm, real, tender.",
  "key_places": ["place 1 (from user's input)", "place 2", "place 3"],
  "key_people": ["important person 1 (from user's input)", "important person 2"],
  "atmosphere": "Atmosphere keywords (3–5, comma-separated)",
  "season_feel": "The seasonal feeling in one sentence"
}

Style: warm, nostalgic, sensory-rich, full of childlike wonder and pure joy.
No negative content, no trauma. Scenes should be specific, real, and emotionally resonant.
Respond ONLY with JSON."""


MEMORY_SCENE_PROMPT = """You are a gentle memory guide helping someone revisit the most beautiful moments of their childhood.

Childhood background:
{childhood_context}

Previous memory fragments:
{previous_scenes}

The person chooses to: {user_choice}

Write a vivid, warm childhood memory scene (~200–250 words):
- Use second person ("you") so the reader feels transported there
- Rich sensory detail: the quality of light, familiar scents, ambient sounds, textures
- Warm, healing, full of innocent joy
- Naturally weave in the friends, places, and activities the person mentioned
- Language should feel honest and grounded — not overwrought or overly literary
- End on a natural image or action that makes the reader want to know what happens next

Output only the scene prose — no title, no heading, no labels."""


MEMORY_CHOICES_PROMPT = """Based on the following childhood memory scene, generate 3 warm "what happens next" choices.

Current scene:
{scene_prose}

Childhood background:
{childhood_context}

Generate 3 choices that fit naturally into a childhood setting:
- Each title should be brief (6–12 words)
- Warm and positive, true to the logic of childhood
- Meaningfully different from each other (e.g. keep playing / find a friend / go somewhere new)
- The description adds a gentle touch of detail (≤12 words)

Output JSON:
{
  "choices": [
    {"title": "Choice title (6–12 words)", "description": "Brief elaboration (≤12 words)"},
    {"title": "Choice title (6–12 words)", "description": "Brief elaboration (≤12 words)"},
    {"title": "Choice title (6–12 words)", "description": "Brief elaboration (≤12 words)"}
  ]
}

Respond ONLY with JSON."""


def build_memory_world(childhood_info: dict) -> dict:
    """Generate a warm nostalgic world configuration from childhood info."""
    log.info("Building memory world from childhood info")
    context = _format_childhood_context(childhood_info)

    response = chat_json(
        messages=[
            {"role": "system", "content": MEMORY_WORLD_PROMPT},
            {"role": "user", "content": f"The person's childhood details:\n{context}"},
        ],
        temperature=0.85,
    )

    try:
        world = json.loads(response)
    except json.JSONDecodeError:
        log.error("Failed to parse memory world JSON: %s", response[:200])
        world = {
            "world_name": "A Childhood Place",
            "description": "A stretch of golden summers — full of laughter, freedom, and the particular magic of being young.",
            "opening_scene": "Afternoon light filters through the leaves and falls in dappled patches across the ground. You stand in a familiar place, a warm breeze brushing your face, carrying the smell of cut grass and something faintly sweet. Somewhere not far away, a friend is calling your name…",
            "key_places": childhood_info.get("favorite_place", "the backyard").split(",")[:3] or ["the backyard", "school", "the creek"],
            "key_people": [childhood_info.get("best_friend", "a childhood friend"), childhood_info.get("family_member", "a family member")],
            "atmosphere": "warm, free, innocent, joyful",
            "season_feel": "The lazy ease of a summer afternoon with nowhere to be"
        }

    log.info("Memory world built: %s", world.get("world_name", "unknown"))
    return world


def generate_memory_scene(childhood_info: dict, previous_scenes: list[str], user_choice: str) -> str:
    """Generate a nostalgic childhood memory scene as free text."""
    log.info("Generating memory scene, choice: %s", user_choice[:40] if user_choice else "start")
    context = _format_childhood_context(childhood_info)
    prev_text = "\n---\n".join(previous_scenes[-2:]) if previous_scenes else "(This is the opening scene.)"

    prompt = MEMORY_SCENE_PROMPT.format(
        childhood_context=context,
        previous_scenes=prev_text,
        user_choice=user_choice or "begin reliving this joyful memory",
    )

    scene = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=600,
    )
    return scene.strip()


def generate_memory_choices(scene_prose: str, childhood_info: dict) -> list[dict]:
    """Generate 3 gentle memory action choices."""
    log.info("Generating memory choices")
    context = _format_childhood_context(childhood_info)

    prompt = MEMORY_CHOICES_PROMPT.format(
        scene_prose=scene_prose[:800],
        childhood_context=context,
    )

    response = chat_json(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
    )

    try:
        data = json.loads(response)
        choices = data.get("choices", [])
        if choices and len(choices) >= 2:
            return choices[:3]
    except (json.JSONDecodeError, KeyError, AttributeError):
        log.warning("Failed to parse memory choices, using defaults")

    friend_name = childhood_info.get("best_friend", "your best friend")
    return [
        {"title": "Keep playing here a little longer", "description": "Savour this moment"},
        {"title": f"Go find {friend_name}", "description": "They're probably nearby"},
        {"title": "Head home and see who's there", "description": "Something smells like it's cooking"},
    ]


def _format_childhood_context(info: dict) -> str:
    """Format childhood info into a readable context string."""
    parts = []
    if info.get("hometown"):
        parts.append(f"Hometown: {info['hometown']}")
    if info.get("best_friend"):
        parts.append(f"Best childhood friend: {info['best_friend']}")
    if info.get("favorite_place"):
        parts.append(f"Favorite childhood place: {info['favorite_place']}")
    if info.get("happy_memory"):
        parts.append(f"A happy memory: {info['happy_memory']}")
    if info.get("favorite_activity"):
        parts.append(f"Favorite game or activity: {info['favorite_activity']}")
    if info.get("family_member"):
        parts.append(f"An important family member: {info['family_member']}")
    if info.get("season"):
        parts.append(f"Favorite season: {info['season']}")
    return "\n".join(parts) if parts else "A beautiful stretch of childhood"
