"""Story and Chapter data models."""
from dataclasses import dataclass, field, asdict


@dataclass
class ChapterPlan:
    chapter_number: int
    title: str
    summary: str
    conflict_level: float = 0.5  # 0.0 - 1.0
    despair_level: float = 0.3  # 0.0 - 1.0
    key_events: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CharacterAction:
    character_id: str
    character_name: str
    public_action: str
    private_thought: str
    dialogue: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Chapter:
    chapter_number: int
    title: str
    prose: str  # final narrative text
    character_actions: list[CharacterAction] = field(default_factory=list)
    safety_score: float = 1.0
    therapeutic_notes: str = ""

    def to_dict(self) -> dict:
        return {
            "chapter_number": self.chapter_number,
            "title": self.title,
            "prose": self.prose,
            "character_actions": [a.to_dict() for a in self.character_actions],
            "safety_score": self.safety_score,
            "therapeutic_notes": self.therapeutic_notes,
        }


@dataclass
class Story:
    session_id: str
    theme: str
    world_config: dict = field(default_factory=dict)
    chapter_plans: list[ChapterPlan] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)
    status: str = "initialized"  # initialized, generating, completed, error

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "theme": self.theme,
            "world_config": self.world_config,
            "chapter_plans": [p.to_dict() for p in self.chapter_plans],
            "chapters": [c.to_dict() for c in self.chapters],
            "status": self.status,
        }
