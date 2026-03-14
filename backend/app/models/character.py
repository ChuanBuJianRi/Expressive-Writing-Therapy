"""Character data model."""
from dataclasses import dataclass, field, asdict


@dataclass
class Character:
    id: str
    name: str
    personality: str
    background: str = ""
    role: str = ""  # e.g. "protagonist", "mentor", "antagonist"
    color: str = "#5b8dee"  # UI display color
    memory: list[dict] = field(default_factory=list)  # past actions/thoughts

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            personality=data.get("personality", ""),
            background=data.get("background", ""),
            role=data.get("role", ""),
            color=data.get("color", "#5b8dee"),
            memory=data.get("memory", []),
        )
