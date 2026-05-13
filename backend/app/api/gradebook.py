from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Assignment, AssignmentGroup, Course, Submission
from app.schemas.gradebook import GradebookGroup, GradebookOut, GradebookRow
from app.services.grading import GradeRow, GroupSpec, course_total, group_percentage

router = APIRouter(tags=["gradebook"], dependencies=[Depends(get_current_user)])


def _aware(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _current_grade(sub: Submission | None):
    return sub.grade if (sub and sub.grade) else None


@router.get("/courses/{course_id}/gradebook", response_model=GradebookOut)
def gradebook(
    course_id: str, only_graded: bool = True, db: Session = Depends(get_db)
) -> GradebookOut:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(404, "course not found")
    groups = {
        g.id: g
        for g in db.query(AssignmentGroup).filter(AssignmentGroup.course_id == course_id).all()
    }
    assignments = (
        db.query(Assignment)
        .filter(Assignment.course_id == course_id, Assignment.published.is_(True))
        .order_by(Assignment.position, Assignment.title)
        .all()
    )
    now = datetime.now(UTC)

    rows: list[GradebookRow] = []
    group_rows: dict[str | None, list[GradeRow]] = {gid: [] for gid in groups}
    group_rows[None] = []
    for a in assignments:
        latest = (
            db.query(Submission)
            .filter(Submission.assignment_id == a.id)
            .order_by(Submission.attempt_number.desc())
            .first()
        )
        grade = _current_grade(latest)
        due = _aware(a.due_at)
        if grade is not None:
            status = "graded"
            score: float | None = float(grade.final_score)
        elif latest is not None:
            status = "submitted"
            score = None
        elif due is not None and now > due:
            status = "missing"
            score = None
        else:
            status = "not_submitted"
            score = None
        gname = groups[a.assignment_group_id].name if a.assignment_group_id in groups else ""
        rows.append(
            GradebookRow(
                assignment_id=a.id,
                title=a.title,
                group_name=gname,
                points_possible=float(a.points_possible),
                due_at=a.due_at,
                submitted_at=latest.submitted_at if latest else None,
                status="late" if (latest and latest.is_late and grade is not None) else status,
                score=score,
                feedback_md=grade.feedback_md if grade else "",
                rubric_breakdown=list(grade.rubric_breakdown) if grade else [],
            )
        )
        if grade is not None:
            key = a.assignment_group_id if a.assignment_group_id in groups else None
            group_rows.setdefault(key, []).append(
                GradeRow(final_score=float(grade.final_score), points=float(a.points_possible))
            )

    gb_groups: list[GradebookGroup] = []
    specs: list[GroupSpec] = []
    for gid, g in groups.items():
        gr = group_rows.get(gid, [])
        pct = group_percentage(gr, g.drop_lowest_n)
        weight = float(g.weight) if g.weight is not None else None
        gb_groups.append(
            GradebookGroup(
                name=g.name,
                weight=weight,
                drop_lowest_n=g.drop_lowest_n,
                percentage=pct,
                earned=sum(r.final_score for r in gr),
                possible=sum(r.points for r in gr),
            )
        )
        specs.append(GroupSpec(name=g.name, weight=weight, drop_lowest_n=g.drop_lowest_n, rows=gr))

    # ungrouped assignments form an implicit unweighted bucket only if there are no weighted groups
    ungrouped = group_rows.get(None, [])
    if ungrouped and all(s.weight is None for s in specs):
        specs.append(GroupSpec(name="(ungrouped)", weight=None, drop_lowest_n=0, rows=ungrouped))

    total = course_total(specs, only_graded=only_graded) if specs else None
    return GradebookOut(
        course_id=course_id,
        rows=rows,
        groups=gb_groups,
        total_percentage=total,
        only_graded=only_graded,
    )
