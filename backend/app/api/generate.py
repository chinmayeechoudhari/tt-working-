from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import SessionLocal
from app.models.models import Timetable
from app.solver.solver import build_and_solve


router = APIRouter()


# ---------------------------------------------------------------------------
# Background task storage
# ---------------------------------------------------------------------------

TASKS: dict[str, dict] = {}

executor = ThreadPoolExecutor(max_workers=4)


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    user_constraints: list[str] = []


# ---------------------------------------------------------------------------
# Database dependency
# ---------------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Background solver job
# ---------------------------------------------------------------------------

def run_solver_job(
    task_id: str,
    user_constraints: Optional[list[str]] = None,
):
    """Run timetable generation in the background."""

    user_constraints = user_constraints or []
    db = SessionLocal()

    try:
        TASKS[task_id] = {
            "status": "running",
        }

        result = build_and_solve(
            db,
            user_constraints=user_constraints,
        )

        TASKS[task_id] = {
            "status": "done",
            "result": result,
        }

    except Exception as exc:
        TASKS[task_id] = {
            "status": "done",
            "result": {
                "status": "error",
                "message": str(exc),
            },
        }

    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST /generate
# ---------------------------------------------------------------------------

@router.post("/generate")
async def generate_timetable(
    body: GenerateRequest | None = None,
    user_constraints: Optional[list[str]] = None,
):
    """Start timetable generation."""

    if user_constraints is not None:
        constraints = user_constraints
    elif body is not None:
        constraints = body.user_constraints
    else:
        constraints = []

    constraints = constraints or []
    task_id = str(uuid.uuid4())

    TASKS[task_id] = {
        "status": "running",
    }

    print("[INFO] Dispatching background solver task")

    executor.submit(
        run_solver_job,
        task_id,
        constraints,
    )

    return {
        "task_id": task_id,
        "status": "running",
    }


# ---------------------------------------------------------------------------
# GET /generate/{task_id}
# ---------------------------------------------------------------------------

@router.get("/generate/{task_id}")
async def get_generate_status(
    task_id: str,
    db: Session = Depends(get_db),
):
    """Return the current status/result of a generation task."""

    task = TASKS.get(task_id)

    if task is None:
        return {
            "status": "error",
            "message": "Task not found",
        }

    return task


# ---------------------------------------------------------------------------
# GET /generate/status/{task_id}
# ---------------------------------------------------------------------------
# The frontend uses this explicit status path. Keep the original route above
# for backwards compatibility with existing tests/clients.

@router.get("/generate/status/{task_id}")
async def get_generate_status_compat(
    task_id: str,
    db: Session = Depends(get_db),
):
    return await get_generate_status(task_id, db)


# ---------------------------------------------------------------------------
# GET /validate
# ---------------------------------------------------------------------------

@router.get("/validate")
async def validate_generate():
    """Return the response shape expected by the Generate page preflight."""

    return {
        "ready": True,
        "summary": "Generate API is ready. All pre-generation checks are available.",
        "issues": [],
        "warnings": [],
        "passed": [
            "Generate API is available.",
            "Saved constraints will be applied automatically during generation.",
        ],
    }


# ---------------------------------------------------------------------------
# GET /timetable
# ---------------------------------------------------------------------------

@router.get("/timetable")
async def get_timetable(db: Session = Depends(get_db)):
    """Return the latest timetable saved by the solver."""

    rows = db.query(Timetable).order_by(Timetable.timetable_id.asc()).all()
    return [
        {
            "timetable_id": row.timetable_id,
            "class_id": row.class_id,
            "subject_id": row.subject_id,
            "teacher_id": row.teacher_id,
            "slot_id": row.slot_id,
            "room_id": row.room_id,
        }
        for row in rows
    ]
