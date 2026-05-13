from datetime import UTC, datetime, timedelta

from app.services.grading import (
    GradeRow,
    GroupSpec,
    apply_late_penalty,
    course_total,
    days_late,
    group_percentage,
)


def test_apply_late_penalty_none_and_flag_only_keep_full_score():
    assert apply_late_penalty(
        score=80, points=100, is_late=True, policy="none", value=None
    ) == (80, 0)
    assert apply_late_penalty(
        score=80, points=100, is_late=True, policy="flag_only", value=None
    ) == (80, 0)
    assert apply_late_penalty(
        score=80, points=100, is_late=False, policy="percent_per_day", value=10, days_late=3
    ) == (80, 0)


def test_apply_late_penalty_percent_per_day():
    assert apply_late_penalty(
        score=80, points=100, is_late=True, policy="percent_per_day", value=10, days_late=3
    ) == (80, 30)
    assert apply_late_penalty(
        score=20, points=100, is_late=True, policy="percent_per_day", value=50, days_late=3
    ) == (20, 100)


def test_group_percentage_drops_lowest():
    rows = [
        GradeRow(final_score=100, points=100),
        GradeRow(final_score=80, points=100),
        GradeRow(final_score=40, points=100),  # dropped
    ]
    assert round(group_percentage(rows, drop_lowest_n=0), 2) == 73.33
    assert group_percentage(rows, drop_lowest_n=1) == 90.0
    assert group_percentage([], drop_lowest_n=0) is None


def test_course_total_weighted_normalizes_over_graded_groups():
    groups = [
        GroupSpec(
            name="Problem Sets",
            weight=50,
            drop_lowest_n=1,
            rows=[GradeRow(100, 100), GradeRow(80, 100), GradeRow(40, 100)],
        ),  # pct 90
        GroupSpec(name="Midterm", weight=20, drop_lowest_n=0, rows=[GradeRow(70, 100)]),  # pct 70
        GroupSpec(name="Final", weight=30, drop_lowest_n=0, rows=[]),  # ungraded
    ]
    assert round(course_total(groups, only_graded=True), 2) == 84.29
    assert round(course_total(groups, only_graded=False), 2) == 59.0


def test_course_total_unweighted_is_flat_points():
    groups = [
        GroupSpec(name="A", weight=None, drop_lowest_n=0, rows=[GradeRow(90, 100)]),
        GroupSpec(name="B", weight=None, drop_lowest_n=0, rows=[GradeRow(40, 50)]),
    ]
    assert round(course_total(groups, only_graded=True), 2) == 86.67


def test_days_late_helper_floor():
    due = datetime(2026, 4, 1, 23, 59, tzinfo=UTC)
    assert days_late(due, due + timedelta(hours=1)) == 1
    assert days_late(due, due + timedelta(days=2, hours=1)) == 3
    assert days_late(due, due - timedelta(hours=1)) == 0
