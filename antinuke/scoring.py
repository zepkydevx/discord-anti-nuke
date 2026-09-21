"""Explainable threat scoring based on how fast and how regularly actions happen.

No Discord objects are used here, so the logic can be unit tested in isolation.
The numbers below are tunable defaults, not absolute truths.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict, deque
from collections.abc import Collection, Iterable

from .models import ThreatAssessment, ThreatEvent, ThreatLevel

# (max average seconds between actions, points). A person needs a couple of
# seconds per deletion (open menu, confirm); a script can take milliseconds.
SPEED_BRACKETS: tuple[tuple[float, int], ...] = (
    (1.0, 70),
    (2.0, 50),
    (4.0, 30),
    (6.0, 15),
)

# (minimum number of actions in the window, points), largest first.
VOLUME_BRACKETS: tuple[tuple[int, int], ...] = ((5, 35), (4, 25), (3, 15))

# Very even spacing is a machine-like trait. It needs at least 4 actions
# (3 intervals): with fewer, "regular" happens by chance too often.
REGULARITY_MIN_EVENTS = 4
REGULARITY_MAX_VARIATION = 0.2  # standard deviation / mean of the intervals
REGULARITY_POINTS = 20

# (minimum score, level), highest first.
LEVEL_THRESHOLDS: tuple[tuple[int, ThreatLevel], ...] = (
    (85, ThreatLevel.CRITICAL),
    (60, ThreatLevel.HIGH),
    (30, ThreatLevel.MEDIUM),
)

MAX_SCORE = 100


class ThreatScorer:
    """Keeps a sliding window of recent actions per (guild, actor) and scores it."""

    def __init__(
        self,
        window_seconds: float = 30.0,
        trusted_ids: Iterable[int] = (),
    ) -> None:
        self._window = window_seconds
        self._trusted = frozenset(trusted_ids)
        self._history: defaultdict[tuple[int, int], deque[ThreatEvent]] = defaultdict(deque)

    def record(self, event: ThreatEvent) -> ThreatAssessment:
        """Register ``event`` and return the updated assessment for its actor."""
        if event.actor_id in self._trusted:
            return ThreatAssessment(0, ThreatLevel.LOW, ("actor is trusted",))

        events = self._history[(event.guild_id, event.actor_id)]
        events.append(event)
        self._drop_old(events, now=event.timestamp)
        return self._assess(events)

    def prune_idle(self, now: float) -> int:
        """Forget actors with no recent activity and return how many were removed."""
        stale = [
            key
            for key, events in self._history.items()
            if not events or now - events[-1].timestamp > self._window
        ]
        for key in stale:
            del self._history[key]
        return len(stale)

    def _drop_old(self, events: deque[ThreatEvent], now: float) -> None:
        """Remove events that fell out of the sliding window."""
        while events and now - events[0].timestamp > self._window:
            events.popleft()

    @staticmethod
    def _assess(events: Collection[ThreatEvent]) -> ThreatAssessment:
        """Turn a window of events into a score, a level and the reasons."""
        times = sorted(event.timestamp for event in events)
        count = len(times)
        if count < 2:
            return ThreatAssessment(0, ThreatLevel.LOW, ("single action, not enough data",))

        intervals = [later - earlier for earlier, later in zip(times, times[1:])]
        average = sum(intervals) / len(intervals)

        reasons: list[str] = []
        kinds = ", ".join(f"{name} x{n}" for name, n in Counter(e.action.value for e in events).items())
        reasons.append(f"{count} actions in the window ({kinds})")

        speed = next((points for limit, points in SPEED_BRACKETS if average <= limit), 0)
        if speed:
            reasons.append(f"average {average:.2f}s between actions (+{speed})")

        volume = next((points for minimum, points in VOLUME_BRACKETS if count >= minimum), 0)
        if volume:
            reasons.append(f"{count} actions in a short time (+{volume})")

        regularity = 0
        if count >= REGULARITY_MIN_EVENTS:
            variation = 0.0 if average == 0 else statistics.pstdev(intervals) / average
            if variation <= REGULARITY_MAX_VARIATION:
                regularity = REGULARITY_POINTS
                reasons.append(f"machine-like regular timing (+{regularity})")

        score = min(MAX_SCORE, speed + volume + regularity)
        level = next((lvl for minimum, lvl in LEVEL_THRESHOLDS if score >= minimum), ThreatLevel.LOW)
        return ThreatAssessment(score, level, tuple(reasons))
