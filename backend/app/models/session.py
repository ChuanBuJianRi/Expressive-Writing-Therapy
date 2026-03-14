"""User session data model."""
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Session:
    id: str
    theme: str
    characters: list[dict] = field(default_factory=list)
    world_config: dict = field(default_factory=dict)
    settings: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "active"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        return cls(
            id=data.get("id", ""),
            theme=data.get("theme", ""),
            characters=data.get("characters", []),
            world_config=data.get("world_config", {}),
            settings=data.get("settings", {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            status=data.get("status", "active"),
        )
