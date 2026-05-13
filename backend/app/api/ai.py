from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Assignment, Submission
from app.schemas.assignment import AiSolutionOut, GradeOut, SolutionInfoOut
from app.services import ai, ai_jobs

router = APIRouter(tags=["ai"], dependencies=[Depends(get_current_user)])


def _assignment(db: Session, assignment_id: str) -> Assignment:
    a = db.get(Assignment, assignment_id)
    if a is None:
        raise HTTPException(404, "assignment not found")
    return a


@router.get("/assignments/{assignment_id}/solution", response_model=SolutionInfoOut)
def get_solution_info(assignment_id: str, db: Session = Depends(get_db)) -> SolutionInfoOut:
    a = _assignment(db, assignment_id)
    kind, _ref = ai_jobs.resolve_key(db, a)
    sol = a.ai_solution
    return SolutionInfoOut(
        assignment_id=a.id,
        key_kind=kind,
        official_solution_url=a.official_solution_url,
        ai_available=ai.ai_available(),
        generation_available=ai.solution_generation_available(),
        ai_solution=AiSolutionOut.model_validate(sol) if sol is not None else None,
    )


@router.post("/assignments/{assignment_id}/generate-solution", response_model=AiSolutionOut)
def generate_solution(assignment_id: str, db: Session = Depends(get_db)) -> AiSolutionOut:
    _assignment(db, assignment_id)
    ai_jobs.ensure_ai_solution(db, assignment_id)
    sol = ai_jobs.run_solution_generation(db, assignment_id)
    return AiSolutionOut.model_validate(sol)


@router.post("/submissions/{submission_id}/regrade", response_model=GradeOut)
def regrade(submission_id: str, db: Session = Depends(get_db)) -> GradeOut:
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(404, "submission not found")
    a = db.get(Assignment, sub.assignment_id)
    if not ai_jobs.has_key(db, a):
        raise HTTPException(
            409, "no solution key — attach one or generate the AI solution first"
        )
    g = ai_jobs.grade_with_ai(db, submission_id)
    if g is None:
        raise HTTPException(502, "AI grading failed — check the submission status / transcript")
    return GradeOut.model_validate(g)
