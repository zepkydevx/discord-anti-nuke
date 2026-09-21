"""Tests for the threat scorer. They run without Discord or a network connection."""

from __future__ import annotations

from collections.abc import Iterable

from antinuke.models import ActionType, ThreatAssessment, ThreatEvent, ThreatLevel
from antinuke.scoring import ThreatScorer

GUILD = 1
ACTOR = 42


def feed(scorer: ThreatScorer, offsets: Iterable[float], actor: int = ACTOR) -> ThreatAssessment:
    """Record one channel deletion per offset (in seconds) and return the last result."""
    result: ThreatAssessment | None = None
    for offset in offsets:
        event = ThreatEvent(GUILD, actor, ActionType.CHANNEL_DELETE, offset)
        result = scorer.record(event)
    assert result is not None
    return result


def test_single_deletion_is_low() -> None:
    result = feed(ThreatScorer(), [0.0])
    assert result.level is ThreatLevel.LOW
    assert result.score == 0


def test_two_slow_deletions_are_low() -> None:
    result = feed(ThreatScorer(), [0.0, 10.0])
    assert result.level is ThreatLevel.LOW


def test_two_very_fast_deletions_are_high() -> None:
    result = feed(ThreatScorer(), [0.0, 0.4])
    assert result.level is ThreatLevel.HIGH
    assert result.score == 70


def test_three_deletions_in_two_seconds_are_critical() -> None:
    result = feed(ThreatScorer(), [0.0, 1.0, 2.0])
    assert result.level is ThreatLevel.CRITICAL
    assert result.score == 85


def test_three_irregular_deletions_in_five_seconds_are_only_medium() -> None:
    result = feed(ThreatScorer(), [0.0, 2.0, 5.5])
    assert result.level is ThreatLevel.MEDIUM


def test_regular_spacing_raises_the_level() -> None:
    irregular = feed(ThreatScorer(), [0.0, 1.0, 4.5, 8.25])
    regular = feed(ThreatScorer(), [0.0, 2.75, 5.5, 8.25])
    assert regular.score > irregular.score
    assert regular.level is ThreatLevel.HIGH


def test_score_never_exceeds_one_hundred() -> None:
    result = feed(ThreatScorer(), [0.0, 0.3, 0.6, 0.9, 1.2])
    assert result.score == 100
    assert result.level is ThreatLevel.CRITICAL


def test_old_events_leave_the_window() -> None:
    result = feed(ThreatScorer(window_seconds=30.0), [0.0, 0.5, 100.0])
    assert result.level is ThreatLevel.LOW


def test_trusted_actor_is_never_flagged() -> None:
    scorer = ThreatScorer(trusted_ids=[ACTOR])
    result = feed(scorer, [0.0, 0.1, 0.2, 0.3, 0.4])
    assert result.level is ThreatLevel.LOW
    assert result.score == 0


def test_actors_are_tracked_separately() -> None:
    scorer = ThreatScorer()
    feed(scorer, [0.0, 0.2, 0.4], actor=1)
    result = feed(scorer, [0.3], actor=2)
    assert result.level is ThreatLevel.LOW


def test_high_threats_explain_themselves() -> None:
    result = feed(ThreatScorer(), [0.0, 0.5, 1.0])
    assert len(result.reasons) >= 2


def test_prune_idle_removes_stale_actors() -> None:
    scorer = ThreatScorer(window_seconds=30.0)
    feed(scorer, [0.0, 1.0])
    assert scorer.prune_idle(now=100.0) == 1
    assert scorer.prune_idle(now=100.0) == 0
