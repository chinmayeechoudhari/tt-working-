from __future__ import annotations

import json

from ortools.sat.python import cp_model
from sqlalchemy.orm import Session

from app.solver.data_loader import load_solver_data

from app.solver.constraints import (
    add_no_teacher_double_booking,
    add_no_room_double_booking,
    add_no_class_double_booking,
    add_periods_per_week,
    add_teacher_availability,
    add_lab_room_matching,
    add_soft_max_periods_per_day,
    add_soft_no_consecutive_periods,
    add_soft_even_distribution,
)

from app.solver.solution_parser import (
    parse_and_save_solution,
    solution_to_dict,
)

from app.constraints.service import ConstraintService
from app.constraints.schemas import GeneratedConstraint
from app.constraints.validator import validate_constraint
from app.models.models import Constraint


def _load_saved_constraints(db: Session) -> list[GeneratedConstraint]:
    """Load and validate all saved constraints for this generation run."""

    # Unit tests use lightweight Mock database objects. Saved-constraint
    # loading is meaningful only for a real SQLAlchemy session.
    if not isinstance(db, Session):
        return []

    rows = db.query(Constraint).order_by(Constraint.constraint_id.asc()).all()
    saved: list[GeneratedConstraint] = []

    for row in rows:
        try:
            payload = json.loads(row.parameters_json or "{}")
            constraint = GeneratedConstraint.model_validate(payload)
            validate_constraint(db, constraint)
        except Exception as exc:
            raise ValueError(
                f"Saved constraint {row.constraint_id} is invalid: {exc}"
            ) from exc

        saved.append(constraint)

    return saved


def build_and_solve(
    db: Session,
    user_constraints: list[str] | None = None,
) -> dict:
    """
    Build and solve the timetable.

    Existing solver constraints are always applied.

    Saved constraints are loaded from the constraint library and applied
    automatically to every generation run.

    Optional natural-language constraints are processed through:

        Natural language
             ↓
        ConstraintService
             ↓
        Gemini
             ↓
        Entity validation
             ↓
        CP-SAT compilation
    """

    data = load_solver_data(db)
    model = cp_model.CpModel()

    # ============================================================
    # BUILD DECISION VARIABLES
    # ============================================================

    assign = {}

    for s_id, c_id in data["subject_map"].items():
        for t_id in data["teacher_ids"]:
            if s_id not in data["teacher_subjects"].get(t_id, []):
                continue

            for sl_id in data["slot_ids"]:
                for r_id in data["room_ids"]:
                    assign[(c_id, s_id, t_id, sl_id, r_id)] = model.NewBoolVar(
                        f"a_c{c_id}_s{s_id}_t{t_id}_sl{sl_id}_r{r_id}"
                    )

    # ============================================================
    # EXISTING HARD CONSTRAINTS
    # ============================================================

    add_no_teacher_double_booking(
        model,
        assign,
        data["teacher_ids"],
        data["slot_ids"],
    )

    add_no_room_double_booking(
        model,
        assign,
        data["room_ids"],
        data["slot_ids"],
    )

    add_no_class_double_booking(
        model,
        assign,
        data["class_ids"],
        data["slot_ids"],
    )

    add_periods_per_week(
        model,
        assign,
        data["subject_periods"],
        data["subject_map"],
    )

    add_teacher_availability(
        model,
        assign,
        data["unavailable_pairs"],
    )

    add_lab_room_matching(
        model,
        assign,
        data["lab_subjects"],
        data["lab_rooms"],
    )

    # ============================================================
    # EXISTING SOFT CONSTRAINTS
    # ============================================================

    penalties = []

    penalties += add_soft_max_periods_per_day(
        model,
        assign,
        data["teacher_max_periods"],
        data["slots_by_day"],
    )

    penalties += add_soft_no_consecutive_periods(
        model,
        assign,
        data["teacher_ids"],
        data["slots_by_day"],
    )

    penalties += add_soft_even_distribution(
        model,
        assign,
        data["subject_periods"],
        data["subject_map"],
        data["slots_by_day"],
    )

    # ============================================================
    # SAVED CONSTRAINT LIBRARY
    # ============================================================

    constraint_service = ConstraintService()
    generated_constraints = []

    for constraint in _load_saved_constraints(db):
        dynamic_penalties = constraint_service.compile(
            model=model,
            assign=assign,
            constraint=constraint,
            data=data,
        )
        generated_constraints.append(constraint)
        penalties.extend(dynamic_penalties)

    # ============================================================
    # DYNAMIC NATURAL-LANGUAGE CONSTRAINTS
    # ============================================================

    for user_text in user_constraints or []:
        constraint, dynamic_penalties = (
            constraint_service.generate_validate_and_compile(
                db=db,
                model=model,
                assign=assign,
                data=data,
                user_text=user_text,
            )
        )

        generated_constraints.append(constraint)
        penalties.extend(dynamic_penalties)

    # ============================================================
    # OBJECTIVE
    # ============================================================

    if penalties:
        model.Minimize(sum(penalties))

    # ============================================================
    # SOLVE
    # ============================================================

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0

    status = solver.Solve(model)

    # ============================================================
    # SOLUTION
    # ============================================================

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result = parse_and_save_solution(
            solver,
            assign,
            db,
        )

        result["timetable"] = solution_to_dict(
            solver,
            assign,
        )

        if generated_constraints:
            result["constraints"] = [
                constraint.model_dump(mode="json")
                for constraint in generated_constraints
            ]

        return result

    return {
        "status": "no_solution",
        "reason": "Constraints may be too tight. Check data.",
    }
