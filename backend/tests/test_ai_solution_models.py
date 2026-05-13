import pytest
from sqlalchemy.exc import IntegrityError

from app.models import AiSolution, Assignment, Course


def test_ai_solution_cascade(db):
    c = Course(code="X", title="X")
    db.add(c)
    db.flush()
    a = Assignment(course_id=c.id, title="PS1", points_possible=100)
    db.add(a)
    db.flush()
    db.add(AiSolution(assignment_id=a.id, status="ready", content_md="# Worked solution"))
    db.commit()

    db.delete(a)
    db.commit()
    assert db.query(AiSolution).count() == 0


def test_ai_solution_assignment_unique(db):
    c = Course(code="Y", title="Y")
    db.add(c)
    db.flush()
    a = Assignment(course_id=c.id, title="PS2", points_possible=100)
    db.add(a)
    db.flush()
    db.add(AiSolution(assignment_id=a.id, status="pending"))
    db.commit()
    db.add(AiSolution(assignment_id=a.id, status="pending"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
