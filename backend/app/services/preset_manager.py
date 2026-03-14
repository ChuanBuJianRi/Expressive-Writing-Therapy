"""Manages preset worlds and characters for quick-start scenarios."""

PRESET_WORLDS = [
    {
        "id": "enchanted_forest",
        "name": "迷雾森林",
        "name_en": "Enchanted Forest",
        "description": "一片被古老魔法笼罩的森林，迷雾中隐藏着治愈与觉醒的秘密。",
        "setting": {
            "time_period": "timeless",
            "atmosphere": "mystical, healing",
            "key_locations": ["古树之心", "月光湖", "回忆小径", "治愈花园"],
            "rules": "森林会回应旅行者内心的情感，恐惧生出迷雾，勇气带来阳光。",
        },
        "tags": ["奇幻", "治愈"],
    },
    {
        "id": "future_city",
        "name": "未来之城",
        "name_en": "Future City",
        "description": "2150年的智慧城市，科技高度发达但人们渐渐失去了情感连接。",
        "setting": {
            "time_period": "2150",
            "atmosphere": "sci-fi, reflective",
            "key_locations": ["情感修复中心", "记忆博物馆", "屋顶花园", "地下旧城"],
            "rules": "城市AI监测市民情绪，低于阈值会被安排'情感修复'。",
        },
        "tags": ["科幻", "现实"],
    },
    {
        "id": "small_town",
        "name": "时光小镇",
        "name_en": "Timeless Town",
        "description": "一个被时间遗忘的南方小镇，居民们各自背负着未曾说出口的故事。",
        "setting": {
            "time_period": "contemporary",
            "atmosphere": "warm, nostalgic, bittersweet",
            "key_locations": ["老茶馆", "河边榕树", "旧书店", "火车站"],
            "rules": "小镇的时间流速与外界不同，在这里人们有机会重新面对过去。",
        },
        "tags": ["现实", "治愈"],
    },
    {
        "id": "dream_realm",
        "name": "梦境之域",
        "name_en": "Dream Realm",
        "description": "一个由众人梦境交织而成的世界，每个人的内心恐惧与渴望在此具象化。",
        "setting": {
            "time_period": "dreamtime",
            "atmosphere": "surreal, emotional, transformative",
            "key_locations": ["镜像大厅", "记忆之海", "恐惧迷宫", "希望灯塔"],
            "rules": "梦境会根据进入者的情感状态不断变化，直面内心才能找到出口。",
        },
        "tags": ["奇幻", "悬疑"],
    },
]

PRESET_CHARACTERS = [
    {
        "id": "healer",
        "name": "林晓",
        "personality": "温柔而坚定，擅长倾听，总能在他人的话语中发现未说出的痛楚。曾经历过深刻的失去。",
        "background": "前心理咨询师，因为一次事故失去了最重要的人。选择踏上旅程，在帮助他人的同时寻找自我治愈。",
        "role": "protagonist",
        "color": "#3ec9a7",
    },
    {
        "id": "guardian",
        "name": "老陈",
        "personality": "沉默寡言但心思细腻，用行动而非语言表达关怀。有着不为人知的温柔过往。",
        "background": "退休的乡村教师，一辈子默默守护着小镇的孩子们。最近开始写回忆录，却发现自己遗忘了太多重要的事。",
        "role": "mentor",
        "color": "#e8c56d",
    },
    {
        "id": "seeker",
        "name": "小鱼",
        "personality": "外表开朗活泼，内心藏着深深的不安。用笑容掩饰恐惧，渴望被真正看见。",
        "background": "大学生，从小在寄养家庭长大。表面上是社交达人，实际上从未真正信任过任何人。",
        "role": "protagonist",
        "color": "#5b8dee",
    },
    {
        "id": "shadow",
        "name": "沈默",
        "personality": "冷淡疏离，言辞犀利，善于看穿他人的伪装。内心深处渴望连接却害怕受伤。",
        "background": "才华横溢的作家，作品描写人性阴暗面。多年前与家人决裂，独自生活。用文字与世界保持安全距离。",
        "role": "antagonist",
        "color": "#9b6dff",
    },
    {
        "id": "innocent",
        "name": "朵朵",
        "personality": "纯真好奇，对世界充满善意。看似天真但有着超越年龄的洞察力。",
        "background": "八岁的小女孩，父母正在闹离婚。在大人的世界里保持着自己的小宇宙，用画画记录一切。",
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
