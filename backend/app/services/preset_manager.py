"""Manages preset worlds and characters for quick-start scenarios."""

PRESET_WORLDS = [
    {
        "id": "enchanted_forest",
        "name": "Enchanted Forest",
        "description": "An ancient forest shrouded in old magic, where the mist conceals secrets of healing and awakening.",
        "setting": {
            "time_period": "timeless",
            "atmosphere": "mystical, healing",
            "key_locations": ["Heart of the Ancient Tree", "Moonlit Lake", "Memory Path", "Healing Garden"],
            "rules": "The forest responds to the inner emotions of wanderers — fear conjures deeper mist, courage brings sunlight.",
            "therapeutic_elements": "The living forest mirrors the inner world, offering a safe space to encounter buried feelings.",
        },
        "tags": ["fantasy", "healing"],
    },
    {
        "id": "future_city",
        "name": "Future City",
        "description": "Year 2150 — a smart city of breathtaking technology where people have slowly lost the ability to feel connected.",
        "setting": {
            "time_period": "2150",
            "atmosphere": "sci-fi, reflective",
            "key_locations": ["Emotional Restoration Center", "Memory Museum", "Rooftop Garden", "Underground Old Quarter"],
            "rules": "The city AI monitors citizen emotional indices. Those below threshold are scheduled for 'Emotional Recalibration'.",
            "therapeutic_elements": "The tension between hyper-efficiency and human longing forces characters to ask: what does it mean to truly feel?",
        },
        "tags": ["sci-fi", "contemporary"],
    },
    {
        "id": "small_town",
        "name": "Timeless Town",
        "description": "A forgotten southern town where time moves differently — and every resident carries a story they have never told.",
        "setting": {
            "time_period": "contemporary",
            "atmosphere": "warm, nostalgic, bittersweet",
            "key_locations": ["The Old Teahouse", "Riverside Banyan Tree", "Second-Hand Bookshop", "The Train Station"],
            "rules": "Time flows slower here than in the outside world. Those who arrive are given a chance to face the past they left behind.",
            "therapeutic_elements": "Stillness and community create the conditions for unsaid truths to finally surface.",
        },
        "tags": ["realistic", "healing"],
    },
    {
        "id": "dream_realm",
        "name": "Dream Realm",
        "description": "A world woven from the tangled dreams of many minds, where each person's deepest fears and desires take physical form.",
        "setting": {
            "time_period": "dreamtime",
            "atmosphere": "surreal, emotional, transformative",
            "key_locations": ["Hall of Mirrors", "Sea of Memory", "The Fear Labyrinth", "Lighthouse of Hope"],
            "rules": "The dreamscape shifts according to the emotional state of those within it. Only by facing what you carry can you find the way out.",
            "therapeutic_elements": "The dream world externalizes the inner unconscious, making the invisible visible and the unspeakable sayable.",
        },
        "tags": ["fantasy", "mystery"],
    },
]

PRESET_CHARACTERS = [
    {
        "id": "healer",
        "name": "Elara",
        "personality": "Gentle yet resolute. A gifted listener who hears what people cannot say. She has known profound loss.",
        "background": "A former therapist who lost the person she loved most in an accident. She left her practice and began wandering, hoping to find healing by helping others — though she hasn't yet healed herself.",
        "role": "protagonist",
        "color": "#3ec9a7",
    },
    {
        "id": "guardian",
        "name": "Old Marcus",
        "personality": "Quiet and unhurried, expressing care through action rather than words. Carries a gentleness he has never shown anyone.",
        "background": "A retired schoolteacher who spent a lifetime watching over the children of a small town. He has begun writing his memoirs, only to discover how much he has forgotten — and how much he misses.",
        "role": "mentor",
        "color": "#e8c56d",
    },
    {
        "id": "seeker",
        "name": "Mira",
        "personality": "Bright and social on the surface, concealing a deep restlessness beneath. Uses laughter to ward off fear. Longs to be truly seen.",
        "background": "A university student who grew up in foster care. She has built an entire social persona, but has never trusted anyone enough to let them close.",
        "role": "protagonist",
        "color": "#5b8dee",
    },
    {
        "id": "shadow",
        "name": "Shade",
        "personality": "Detached and sharp-tongued. Sees through pretense effortlessly. Craves connection in secret while fearing it above all else.",
        "background": "A brilliant writer whose work dissects human darkness. He severed ties with his family years ago and lives alone. His prose is the only place he tells the truth.",
        "role": "antagonist",
        "color": "#9b6dff",
    },
    {
        "id": "innocent",
        "name": "Dot",
        "personality": "Curious, open-hearted, and full of wonder. Appears naive but possesses an unsettling insight beyond her years.",
        "background": "An eight-year-old girl whose parents are separating. She maintains her own small universe inside the adult world, recording everything in drawings that tell more than words can.",
        "role": "catalyst",
        "color": "#f06292",
    },
]


def get_preset_worlds() -> list[dict]:
    return PRESET_WORLDS


def get_preset_characters() -> list[dict]:
    return PRESET_CHARACTERS


def get_world_by_id(world_id: str) -> dict | None:
    for w in PRESET_WORLDS:
        if w["id"] == world_id:
            return w
    return None


def get_character_by_id(char_id: str) -> dict | None:
    for c in PRESET_CHARACTERS:
        if c["id"] == char_id:
            return c
    return None
