from datetime import UTC, datetime

from app.models import Assignment, Course, Grade, Submission


def test_submission_grade_cascade(db):
    c = Course(code="X", title="X")
    db.add(c)
    db.flush()
    a = Assignment(course_id=c.id, title="PS1", points_possible=100)
    db.add(a)
    db.flush()
    s = Submission(assignment_id=a.id, submitted_at=datetime.now(UTC), file_paths=["p/x.pdf"])
    db.add(s)
    db.flush()
    db.add(Grade(submission_id=s.id, score=90, score_out_of=100, final_score=90, percentage=90))
    db.commit()

    db.delete(a)
    db.commit()
    assert db.query(Submission).count() == 0
    assert db.query(Grade).count() == 0
