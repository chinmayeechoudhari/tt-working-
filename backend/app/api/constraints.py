from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.constraints.resolver import EntityResolutionError, resolve_subject_candidates
from app.constraints.schemas import GeneratedConstraint
from app.constraints.service import ConstraintService
from app.constraints.validator import ConstraintValidationError, validate_constraint
from app.core.config import get_db
from app.models.models import Constraint


router = APIRouter(prefix="/constraints", tags=["constraints"])
service = ConstraintService()


class ConstraintSelection(BaseModel):
    subject_id: int
    class_id: int
    subject_type: str


class ConstraintRequest(BaseModel):
    text: str
    selection: ConstraintSelection | None = None


class SaveConstraintRequest(BaseModel):
    constraint: GeneratedConstraint


def _serialize(row: Constraint) -> dict:
    try:
        payload = json.loads(row.parameters_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    return {"constraint_id": row.constraint_id, "constraint_name": row.constraint_name, "constraint_type": row.constraint_type, "constraint": payload}


def _walk_conditions(condition: Any):
    if condition.kind == "atomic":
        yield condition
    elif condition.kind in ("and", "or"):
        for child in condition.conditions:
            yield from _walk_conditions(child)
    elif condition.kind == "not":
        yield from _walk_conditions(condition.condition)


def _subject_context(constraint: GeneratedConstraint):
    expression = constraint.expression
    conditions = []
    if expression.kind in ("forbid", "exists", "no_adjacent", "count"):
        conditions = list(_walk_conditions(expression.filter))
    elif expression.kind == "comparison":
        for side in (expression.left, expression.right):
            if side.kind == "count":
                conditions.extend(_walk_conditions(side.filter))
    elif expression.kind == "for_each":
        return _subject_context_from_expression(expression.expression)
    return _context_from_atoms(conditions)


def _subject_context_from_expression(expression):
    if expression.kind in ("forbid", "exists", "no_adjacent", "count"):
        return _context_from_atoms(list(_walk_conditions(expression.filter)))
    if expression.kind == "comparison":
        atoms = []
        for side in (expression.left, expression.right):
            if side.kind == "count":
                atoms.extend(_walk_conditions(side.filter))
        return _context_from_atoms(atoms)
    if expression.kind == "for_each":
        return _subject_context_from_expression(expression.expression)
    return {"subject": None, "class": None, "subject_type": None}


def _context_from_atoms(atoms):
    result = {"subject": None, "class": None, "subject_type": None}
    for atom in atoms:
        if atom.field in result and result[atom.field] is None and atom.operator == "eq":
            result[atom.field] = str(atom.value)
    return result


def _bound_subject_candidates(db: Session, context: dict):
    candidates = resolve_subject_candidates(db, context["subject"])
    requested_class = context.get("class")
    requested_type = context.get("subject_type")
    if requested_class:
        normalized = requested_class.strip().lower()
        candidates = [s for s in candidates if str(s.class_id) == requested_class or str(s.class_.class_name).strip().lower() == normalized]
    if requested_type:
        candidates = [s for s in candidates if str(s.subject_type).strip().lower() == requested_type.strip().lower()]
    return candidates


def _global_no_class_day_constraint(text: str) -> GeneratedConstraint | None:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    match = re.fullmatch(r"(?:no|none|nothing)\s+(?:classes?|lectures?|teaching|periods?)\s+(?:on|for)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\.?", normalized)
    if not match:
        return None
    day = match.group(1).capitalize()
    from app.constraints.schemas import AtomicCondition, ForbidExpression
    return GeneratedConstraint(constraint_type="hard", weight=None, expression=ForbidExpression(filter=AtomicCondition(field="day", operator="eq", value=day)), explanation=f"No classes may be scheduled on {day}.", assumptions=[])


def _append_atomic_to_condition(condition, atom):
    if condition.kind == "and":
        condition.conditions.append(atom)
        return condition
    from app.constraints.schemas import AndCondition
    return AndCondition(conditions=[condition, atom])


def _apply_selection(constraint: GeneratedConstraint, selection: ConstraintSelection) -> GeneratedConstraint:
    from app.constraints.schemas import AtomicCondition
    def bind_expression(expression):
        if expression.kind in ("forbid", "exists", "no_adjacent"):
            expression.filter = _append_atomic_to_condition(expression.filter, AtomicCondition(field="class", operator="eq", value=str(selection.class_id)))
            expression.filter = _append_atomic_to_condition(expression.filter, AtomicCondition(field="subject_type", operator="eq", value=selection.subject_type))
            return expression
        if expression.kind == "comparison":
            for side in (expression.left, expression.right):
                if side.kind == "count":
                    side.filter = _append_atomic_to_condition(side.filter, AtomicCondition(field="class", operator="eq", value=str(selection.class_id)))
                    side.filter = _append_atomic_to_condition(side.filter, AtomicCondition(field="subject_type", operator="eq", value=selection.subject_type))
            return expression
        if expression.kind == "for_each":
            expression.expression = bind_expression(expression.expression)
            return expression
        return expression
    return constraint.model_copy(update={"expression": bind_expression(constraint.expression)})


def _subject_clarification(db: Session, constraint: GeneratedConstraint):
    context = _subject_context(constraint)
    subject_name = context.get("subject")
    if not subject_name:
        return None
    candidates = _bound_subject_candidates(db, context)
    all_candidates = resolve_subject_candidates(db, subject_name)
    if len(all_candidates) <= 1 or len(candidates) <= 1:
        return None
    return {
        "status": "needs_clarification",
        "message": f"'{subject_name}' is registered for multiple classes or subject types. Please select the exact class and type before applying this rule.",
        "subject": subject_name,
        "options": [{"subject_id": s.subject_id, "subject_name": s.subject_name, "class_id": s.class_id, "class_name": s.class_.class_name, "subject_type": s.subject_type or "theory"} for s in candidates],
        "constraint": constraint.model_dump(mode="json"),
    }


def _validate_for_constraint_studio(db: Session, constraint: GeneratedConstraint) -> None:
    try:
        validate_constraint(db, constraint)
        return
    except EntityResolutionError as exc:
        context = _subject_context(constraint)
        if "Multiple subjects matched" in str(exc) and context.get("subject") and len(_bound_subject_candidates(db, context)) == 1:
            return
        raise


@router.post("/preview")
def preview_constraint(request: ConstraintRequest, db: Session = Depends(get_db)):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Constraint text cannot be empty")
    try:
        constraint = _global_no_class_day_constraint(text) or service.generator.generate(text)
        if request.selection is not None:
            constraint = _apply_selection(constraint, request.selection)
        else:
            clarification = _subject_clarification(db, constraint)
            if clarification is not None:
                return clarification
        _validate_for_constraint_studio(db, constraint)
    except (EntityResolutionError, ConstraintValidationError, ValueError, ValidationError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "valid", "constraint": constraint.model_dump(mode="json")}


@router.get("")
def list_constraints(db: Session = Depends(get_db)):
    rows = db.query(Constraint).order_by(Constraint.constraint_id.desc()).all()
    return [_serialize(row) for row in rows]


@router.post("")
def create_constraint(request: SaveConstraintRequest, db: Session = Depends(get_db)):
    constraint = request.constraint
    try:
        _validate_for_constraint_studio(db, constraint)
    except (EntityResolutionError, ConstraintValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = constraint.model_dump(mode="json")
    parameters_json = json.dumps(payload, sort_keys=True)
    duplicate = db.query(Constraint).filter(Constraint.parameters_json == parameters_json).first()
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="This constraint is already active.")
    row = Constraint(constraint_name=constraint.explanation, constraint_type=constraint.constraint_type, parameters_json=parameters_json)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.delete("/{constraint_id}")
def delete_constraint(constraint_id: int, db: Session = Depends(get_db)):
    row = db.query(Constraint).filter(Constraint.constraint_id == constraint_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Constraint not found")
    db.delete(row)
    db.commit()
    return {"status": "deleted", "constraint_id": constraint_id}
