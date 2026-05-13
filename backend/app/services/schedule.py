"""Pure scheduling math for a course.

Given a start date and two cadences (days between lectures, days between problem sets),
compute a proposed due_at for every assignment using the user's stated rule:

  > Assignment k's deadline is the day before the next lecture that is NOT covered
  > by the assignment (i.e. the next lecture beyond `covers_lecture_to`).

If an assignment has no `covers_lecture_to`, fall back to evenly spacing it at
`start_date + (position_in_group + 1) * homework_cadence_days`. If it covers
beyond the last lecture (e.g. final exam), put the deadline a buffer after the
last lecture: `start_date + (last_lec - 1) * lecture_cadence + buffer_days`.

No I/O. The HTTP layer in ``api/schedule.py`` calls this and persists the result.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta


@dataclass(frozen=True)
class AssignmentLite:
    """Just the fields the scheduler needs."""

    id: str
    title: str
    position: int
    assignment_group_id: str | None
    covers_lecture_from: int | None
    covers_lecture_to: int | None


@dataclass
class ScheduleParams:
    start_date: datetime  # day of Lecture 1 (UTC midnight is fine)
    lecture_cadence_days: int  # days between lectures
    homework_cadence_days: int  # fallback days between PS deadlines
    num_lectures: int  # max lecture number in the course (23 for 18.100B)
    buffer_after_last_lecture_days: int = 7  # for assignments that cover everything
    due_time: time = time(hour=23, minute=59)  # local time used for due_at


def _lecture_date(start_date: datetime, n: int, cadence: int) -> datetime:
    return start_date + timedelta(days=(n - 1) * cadence)


def _at_due_time(d: datetime, due_time: time) -> datetime:
    """Replace the time component of ``d`` with ``due_time`` (kept tz-aware)."""
    return d.replace(
        hour=due_time.hour, minute=due_time.minute, second=0, microsecond=0
    )


def compute_due(a: AssignmentLite, p: ScheduleParams) -> datetime:
    """Compute one assignment's due_at per the rules above."""
    cadence = p.lecture_cadence_days
    last_lec = p.num_lectures

    if a.covers_lecture_to is not None and a.covers_lecture_to >= 1:
        next_lec = a.covers_lecture_to + 1
        if next_lec <= last_lec:
            # Day before the next non-covered lecture.
            due_day = _lecture_date(p.start_date, next_lec, cadence) - timedelta(days=1)
        else:
            # Covers the rest of the course (e.g. Final). Buffer after the last lecture.
            due_day = _lecture_date(p.start_date, last_lec, cadence) + timedelta(
                days=p.buffer_after_last_lecture_days
            )
        return _at_due_time(due_day, p.due_time)

    # No coverage info: even-spacing fallback by position within group.
    days = (a.position + 1) * p.homework_cadence_days
    return _at_due_time(p.start_date + timedelta(days=days), p.due_time)


def compute_schedule(
    assignments: list[AssignmentLite], params: ScheduleParams
) -> dict[str, datetime]:
    """Return {assignment_id: due_at} for every assignment in input order."""
    return {a.id: compute_due(a, params) for a in assignments}


def parse_start_date(s: str) -> datetime:
    """Accept 'YYYY-MM-DD' or full ISO; return a tz-aware UTC datetime at 00:00:00."""
    try:
        # plain date first
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
