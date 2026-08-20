from __future__ import annotations

from app.constraints.schemas import GeneratedConstraint
from app.constraints.resolver import (
    EntityResolutionError,
    resolve_teacher,
    resolve_subject_candidates,
    resolve_class,
    resolve_room,
    resolve_day_slots,
    resolve_slot,
    resolve_period,
    parse_slot_value,
)
from app.models.models import Room, Subject


class ConstraintValidationError(Exception):
    """Raised when a generated constraint is invalid."""
    pass


def validate_constraint(db, constraint: GeneratedConstraint) -> bool:
    _validate_expression(db, constraint.expression)
    return True


def _validate_expression(db, expression):
    kind = expression.kind
    if kind == "comparison":
        _validate_numeric_expression(db, expression.left)
        _validate_numeric_expression(db, expression.right)
        return
    if kind in ("forbid", "exists", "no_adjacent"):
        _validate_condition(db, expression.filter)
        return
    if kind == "for_each":
        _validate_expression(db, expression.expression)
        return
    raise ConstraintValidationError(f"Unsupported expression type: {kind}")


def _validate_numeric_expression(db, expression):
    if expression.kind == "constant":
        return
    if expression.kind == "count":
        _validate_condition(db, expression.filter)
        return
    raise ConstraintValidationError(f"Unsupported numeric expression: {expression.kind}")


def _validate_condition(db, condition, context: dict | None = None):
    """Validate conditions while carrying class/type scope into subjects."""
    context = dict(context or {})
    kind = condition.kind

    if kind == "atomic":
        _validate_atomic_condition(db, condition, context=context)
        return

    if kind == "and":
        local_context = dict(context)
        for child in condition.conditions:
            if child.kind == "atomic" and child.operator == "eq" and child.field in {"class", "subject_type"}:
                local_context[child.field] = child.value

        for child in condition.conditions:
            _validate_condition(db, child, context=local_context)
        return

    if kind == "or":
        for child in condition.conditions:
            _validate_condition(db, child, context=context)
        return

    if kind == "not":
        _validate_condition(db, condition.condition, context=context)
        return

    raise ConstraintValidationError(f"Unsupported condition type: {kind}")


def _validate_atomic_condition(db, condition, *, context: dict | None = None) -> None:
    field = condition.field
    value = condition.value
    context = context or {}

    if field == "teacher":
        resolve_teacher(db, str(value))
    elif field == "subject":
        _resolve_subject_in_context(db, str(value), context)
    elif field == "class":
        resolve_class(db, str(value))
    elif field == "room":
        resolve_room(db, str(value))
    elif field == "day":
        resolve_day_slots(db, str(value))
    elif field == "period":
        if isinstance(value, bool):
            raise EntityResolutionError(f"Period '{value}' must be an integer.")
        try:
            period = int(value)
        except (TypeError, ValueError) as exc:
            raise EntityResolutionError(f"Period '{value}' must be an integer.") from exc
        resolve_period(db, period)
    elif field == "slot":
        day, period = parse_slot_value(value)
        resolve_slot(db, day, period)
    elif field == "room_type":
        requested = str(value).strip().lower()
        available = {
            str(room.room_type).strip().lower()
            for room in db.query(Room).all()
            if room.room_type is not None
        }
        if requested not in available:
            raise EntityResolutionError(f"Room type '{value}' was not found.")
    elif field == "subject_type":
        requested = str(value).strip().lower()
        available = {
            str(subject.subject_type).strip().lower()
            for subject in db.query(Subject).all()
            if subject.subject_type is not None
        }
        if requested not in available:
            raise EntityResolutionError(f"Subject type '{value}' was not found.")
    else:
        raise ConstraintValidationError(f"Unsupported condition field: {field}")


def _resolve_subject_in_context(db, name: str, context: dict) -> None:
    """Resolve a subject, optionally narrowed by class and subject type."""
    candidates = resolve_subject_candidates(db, name)
    if len(candidates) <= 1:
        return

    class_value = context.get("class")
    if class_value is not None:
        class_entity = resolve_class(db, str(class_value))
        candidates = [
            subject for subject in candidates
            if subject.class_id == class_entity.class_id
        ]

    subject_type = context.get("subject_type")
    if subject_type is not None:
        requested = str(subject_type).strip().lower()
        candidates = [
            subject for subject in candidates
            if str(subject.subject_type or "theory").strip().lower() == requested
        ]

    if len(candidates) == 1:
        return
    if not candidates:
        raise EntityResolutionError(
            f"Subject '{name}' does not have a registration matching the selected class/type."
        )

    names = ", ".join(str(getattr(subject, "subject_name", name)) for subject in candidates[:5])
    raise EntityResolutionError(f"Multiple subjects matched '{name}': {names}.")
