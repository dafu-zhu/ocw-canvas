"""Pure grading math: late penalties, per-group percentages with drop rules, course rollup.

No I/O — everything takes plain data so it is exhaustively unit-tested.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GradeRow:
    final_score: float
    points: float


@dataclass
class GroupSpec:
    name: str
    weight: float | None
    drop_lowest_n: int
    rows: list[GradeRow] = field(default_factory=list)


def days_late(due_at: datetime, submitted_at: datetime) -> int:
    """Whole days late (1-based: any time past the deadline is day 1). 0 if on time."""
    if submitted_at <= due_at:
        return 0
    delta = submitted_at - due_at
    return int(math.floor(delta.total_seconds() / 86400)) + 1


def apply_late_penalty(
    *,
    score: float,
    points: float,
    is_late: bool,
    policy: str,
    value: float | None,
    days_late: int = 0,
) -> tuple[float, float]:
    """Return (score_unchanged, penalty_points). The caller does final = max(0, score - penalty)."""
    if not is_late or policy in ("none", "flag_only"):
        return score, 0.0
    if policy == "percent_per_day":
        pct = (value or 0) * max(days_late, 1)
        penalty = min(points, points * pct / 100.0)
        return score, penalty
    return score, 0.0


def days_late_between(due_at: datetime | None, submitted_at: datetime | None) -> int:
    """``days_late`` but tolerant of None and of SQLite's naive datetimes (assumed UTC)."""
    if due_at is None or submitted_at is None:
        return 0
    if due_at.tzinfo is None and submitted_at.tzinfo is not None:
        from datetime import UTC

        due_at = due_at.replace(tzinfo=UTC)
    elif submitted_at.tzinfo is None and due_at.tzinfo is not None:
        from datetime import UTC

        submitted_at = submitted_at.replace(tzinfo=UTC)
    return days_late(due_at, submitted_at)


def finalize_score(
    *,
    score: float,
    points: float,
    is_late: bool,
    policy: str,
    value: float | None,
    days_late: int = 0,
) -> tuple[float, float, float]:
    """The single late-penalty/finalisation path used by both manual and AI grading.

    Returns ``(penalty_points, final_score, percentage)``."""
    _, penalty = apply_late_penalty(
        score=score, points=points, is_late=is_late, policy=policy, value=value, days_late=days_late
    )
    final = max(0.0, score - penalty)
    pct = (final / points * 100.0) if points else 0.0
    return penalty, final, pct


def group_percentage(rows: list[GradeRow], drop_lowest_n: int) -> float | None:
    """Σ final_score / Σ points over graded rows, after dropping the N lowest by percentage.
    None if there are no graded rows (or all get dropped)."""
    graded = [r for r in rows if r.points > 0]
    if not graded:
        return None
    if drop_lowest_n > 0:
        graded = sorted(graded, key=lambda r: r.final_score / r.points)[drop_lowest_n:]
    if not graded:
        return None
    total_pts = sum(r.points for r in graded)
    if total_pts == 0:
        return None
    return sum(r.final_score for r in graded) / total_pts * 100.0


def course_total(groups: list[GroupSpec], *, only_graded: bool) -> float | None:
    """Weighted sum of group percentages if every group has a weight; otherwise a flat
    points total. only_graded=True excludes ungraded groups and renormalizes the remaining
    weights; only_graded=False makes an ungraded weighted group contribute 0%."""
    weighted = bool(groups) and all(g.weight is not None for g in groups)
    if not weighted:
        rows = [r for g in groups for r in g.rows if r.points > 0]
        if not rows:
            return None
        total_pts = sum(r.points for r in rows)
        if total_pts == 0:
            return None
        return sum(r.final_score for r in rows) / total_pts * 100.0

    contributions: list[tuple[float, float]] = []  # (weight, percentage)
    for g in groups:
        pct = group_percentage(g.rows, g.drop_lowest_n)
        if pct is None:
            if only_graded:
                continue
            pct = 0.0
        contributions.append((g.weight or 0.0, pct))
    if not contributions:
        return None
    weight_sum = sum(w for w, _ in contributions)
    if weight_sum == 0:
        return None
    return sum(w * p for w, p in contributions) / weight_sum
