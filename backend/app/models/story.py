"""Story, Chapter, Scene, and related data models."""
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ChapterPlan:
    chapter_number: int
    title: str
    summary: str
    conflict_level: float = 0.5
    despair_level: float = 0.3
    key_events: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScenePlan:
    """A single scene within a chapter — the unit of generation."""
    scene_number: int           # within the chapter
    title: str
    description: str            # what happens in this scene
    tension_level: float = 0.4  # 0.0 (calm) → 1.0 (crisis peak)
    is_decision_point: bool = False  # should user choose here?
    involved_characters: list[str] = field(default_factory=list)  # character ids
    hard_event: str = ""        # the concrete irreversible event that must occur

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CharacterAction:
    character_id: str
    character_name: str
    public_action: str
    private_thought: str
    dialogue: str
    emotional_state: str = ""
    growth_moment: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Scene:
    """A generated scene: prose + tension metadata."""
    scene_number: int
    title: str
    prose: str
    tension_level: float = 0.4
    is_decision_point: bool = False
    character_actions: list[CharacterAction] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scene_number": self.scene_number,
            "title": self.title,
            "prose": self.prose,
            "tension_level": self.tension_level,
            "is_decision_point": self.is_decision_point,
            "character_actions": [a.to_dict() for a in self.character_actions],
        }


@dataclass
class Chapter:
    chapter_number: int
    title: str
    scenes: list[Scene] = field(default_factory=list)
    safety_score: float = 1.0
    therapeutic_notes: str = ""
    # If chapter was cut at a decision point, store which scene triggered it
    decision_scene: Optional[int] = None

    @property
    def prose(self) -> str:
        """Concatenate all scene prose into chapter prose."""
        return "\n\n".join(s.prose for s in self.scenes if s.prose.strip())

    def to_dict(self) -> dict:
        return {
            "chapter_number": self.chapter_number,
            "title": self.title,
            "prose": self.prose,
            "scenes": [s.to_dict() for s in self.scenes],
            "safety_score": self.safety_score,
            "therapeutic_notes": self.therapeutic_notes,
            "decision_scene": self.decision_scene,
            # legacy compat: also expose character_actions flat
            "character_actions": [
                a.to_dict()
                for s in self.scenes
                for a in s.character_actions
            ],
        }


@dataclass
class Story:
    session_id: str
    theme: str
    world_config: dict = field(default_factory=dict)
    chapter_plans: list[ChapterPlan] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)
    # Characters: split into core (set at start) and story (added mid-story)
    core_characters: list[dict] = field(default_factory=list)
    story_characters: list[dict] = field(default_factory=list)
    status: str = "initialized"

    @property
    def all_characters(self) -> list[dict]:
        return self.core_characters + self.story_characters

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "theme": self.theme,
            "world_config": self.world_config,
            "chapter_plans": [p.to_dict() for p in self.chapter_plans],
            "chapters": [c.to_dict() for c in self.chapters],
            "core_characters": self.core_characters,
            "story_characters": self.story_characters,
            "status": self.status,
        }
