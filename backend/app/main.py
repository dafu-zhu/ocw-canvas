from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    ai,
    announcements,
    assignment_groups,
    assignments,
    auth,
    courses,
    cron,
    files,
    gradebook,
    module_items,
    modules,
    submissions,
)
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="OCW Canvas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(courses.router, prefix="/api")
app.include_router(modules.router, prefix="/api")
app.include_router(module_items.router, prefix="/api")
app.include_router(assignment_groups.router, prefix="/api")
app.include_router(assignments.router, prefix="/api")
app.include_router(submissions.router, prefix="/api")
app.include_router(gradebook.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(announcements.router, prefix="/api")
app.include_router(cron.router, prefix="/api")
app.include_router(files.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
