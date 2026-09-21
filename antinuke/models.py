"""Plain data types shared across the anti-nuke modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum


class ActionType(str, Enum):
    """Destructive actions the detector keeps track of."""

    CHANNEL_DELETE = "channel_delete"
    ROLE_DELETE = "role_delete"
    MEMBER_BAN = "member_ban"
    MEMBER_KICK = "member_kick"


class ThreatLevel(IntEnum):
    """Severity buckets, ordered so they can be compared (HIGH > MEDIUM)."""

    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


@dataclass(frozen=True)
class ThreatEvent:
    """A single destructive action performed by someone in a guild."""

    guild_id: int
    actor_id: int
    action: ActionType
    timestamp: float  # seconds; prefer the audit-log entry time over arrival time


@dataclass(frozen=True)
class ThreatAssessment:
    """Result of scoring an actor's recent behaviour.

    ``reasons`` explains how the score was built, so every automatic action
    can be justified in the logs.
    """

    score: int
    level: ThreatLevel
    reasons: tuple[str, ...] = field(default_factory=tuple)
