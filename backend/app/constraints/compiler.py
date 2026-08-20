from __future__ import annotations

from typing import Any

from ortools.sat.python import cp_model

from app.constraints.schemas import GeneratedConstraint, Condition
from app.constraints.resolver import (
    resolve_teacher,
    resolve_subject,
    resolve_subjects,
    resolve_class,
    resolve_room,
    parse_slot_value,
    resolve_slot,
)


def compile_constraint(model: cp_model.CpModel, assign: dict, constraint: GeneratedConstraint, data: dict) -> list:
    penalties = []
    expression = constraint.expression

    if expression.kind == "comparison":
        penalties.extend(_compile_comparison(model, assign, expression, constraint.constraint_type, data))
    elif expression.kind == "forbid":
        _compile_forbid(model, assign, expression, data)
    elif expression.kind == "exists":
        penalties.extend(_compile_exists(model, assign, expression, constraint.constraint_type, data))
    elif expression.kind == "no_adjacent":
        penalties.extend(_compile_no_adjacent(model, assign, expression, constraint.constraint_type, data))
    elif expression.kind == "for_each":
        raise NotImplementedError("for_each constraints are not supported yet.")
    else:
        raise ValueError(f"Unsupported expression kind: {expression.kind}")

    return penalties


def _matching_variables(assign: dict, condition: Condition, data: dict) -> list:
    if condition.kind == "atomic":
        return _matching_atomic_variables(assign, condition.field, condition.operator, condition.value, data)

    if condition.kind == "and":
        sets = [set(_matching_variables(assign, child, data)) for child in condition.conditions]
        if not sets:
            return []
        result = sets[0]
        for current in sets[1:]:
            result &= current
        return list(result)

    if condition.kind == "or":
        result = set()
        for child in condition.conditions:
            result.update(_matching_variables(assign, child, data))
        return list(result)

    if condition.kind == "not":
        all_variables = set(assign.values())
        matching = set(_matching_variables(assign, condition.condition, data))
        return list(all_variables - matching)

    raise ValueError(f"Unsupported condition kind: {condition.kind}")


def _matching_atomic_variables(assign: dict, field: str, operator: str, value: Any, data: dict) -> list:
    expected_values = _resolve_expected_values(field, value, data)
    result = []

    for (class_id, subject_id, teacher_id, slot_id, room_id), variable in assign.items():
        actual = _get_field_value(field, class_id, subject_id, teacher_id, slot_id, room_id, data)
        if any(_compare(actual, operator, expected) for expected in expected_values):
            result.append(variable)

    return result


def _resolve_expected_value(field: str, value: Any, data: dict) -> Any:
    """Translate Gemini's human-readable entity values into solver IDs."""

    db = data.get("db")

    # Existing unit tests use integer IDs directly and don't provide a DB.
    if db is None:
        if field == "period":
            try:
                return int(value)
            except (TypeError, ValueError):
                return value
        return value

    if field == "teacher":
        return resolve_teacher(db, str(value)).teacher_id
    if field == "subject":
        return resolve_subject(db, str(value)).subject_id
    if field == "class":
        return resolve_class(db, str(value)).class_id
    if field == "room":
        return resolve_room(db, str(value)).room_id
    if field == "day":
        return str(value).strip()
    if field == "period":
        return int(value)
    if field == "slot":
        day, period = parse_slot_value(value)
        return resolve_slot(db, day, period).slot_id
    if field == "room_type":
        return str(value).strip().lower()
    if field == "subject_type":
        return str(value).strip().lower()
    return value


def _resolve_expected_values(field: str, value: Any, data: dict) -> list[Any]:
    """Return all valid IDs when an entity name is repeated across scopes."""
    db = data.get("db")
    if db is not None and field == "subject":
        return [subject.subject_id for subject in resolve_subjects(db, str(value))]
    return [_resolve_expected_value(field, value, data)]


def _get_field_value(field: str, class_id: int, subject_id: int, teacher_id: int, slot_id: int, room_id: int, data: dict):
    if field == "teacher":
        return teacher_id
    if field == "subject":
        return subject_id
    if field == "class":
        return class_id
    if field == "room":
        return room_id
    if field == "slot":
        return slot_id
    if field == "day":
        return data["slot_day"][slot_id]
    if field == "period":
        return data["slot_period"][slot_id]
    if field == "room_type":
        return data["room_types"][room_id]
    if field == "subject_type":
        return data["subject_types"][subject_id]
    raise ValueError(f"Unsupported condition field: {field}")


def _compile_comparison(model, assign, expression, constraint_type, data):
    left = expression.left
    right = expression.right
    if left.kind != "count":
        raise NotImplementedError("Currently only COUNT expressions are supported on the left side.")
    if right.kind != "constant":
        raise NotImplementedError("Currently only constant values are supported on the right side.")

    variables = _matching_variables(assign, left.filter, data)
    count = sum(variables) if variables else 0
    limit = right.value
    operator = expression.operator

    if constraint_type == "hard":
        if operator == "eq": model.Add(count == limit)
        elif operator == "neq": model.Add(count != limit)
        elif operator == "lt": model.Add(count < limit)
        elif operator == "lte": model.Add(count <= limit)
        elif operator == "gt": model.Add(count > limit)
        elif operator == "gte": model.Add(count >= limit)
        else: raise ValueError(f"Unsupported comparison operator: {operator}")
        return []

    return [_create_comparison_penalty(model, count, operator, limit)]


def _create_comparison_penalty(model, count, operator, limit):
    upper_bound = max(0, int(limit) + 100)
    if operator == "lte":
        penalty = model.NewIntVar(0, upper_bound, "dynamic_penalty_lte")
        model.Add(penalty >= count - limit)
        return penalty
    if operator == "lt":
        penalty = model.NewIntVar(0, upper_bound, "dynamic_penalty_lt")
        model.Add(penalty >= count - (limit - 1))
        return penalty
    if operator == "gte":
        penalty = model.NewIntVar(0, upper_bound, "dynamic_penalty_gte")
        model.Add(penalty >= limit - count)
        return penalty
    if operator == "gt":
        penalty = model.NewIntVar(0, upper_bound, "dynamic_penalty_gt")
        model.Add(penalty >= (limit + 1) - count)
        return penalty
    if operator == "eq":
        penalty = model.NewIntVar(0, upper_bound, "dynamic_penalty_eq")
        model.Add(penalty >= count - limit)
        model.Add(penalty >= limit - count)
        return penalty
    if operator == "neq":
        raise NotImplementedError("Soft 'neq' constraints are not supported yet.")
    raise ValueError(f"Unsupported comparison operator: {operator}")


def _compile_forbid(model, assign, expression, data):
    for variable in _matching_variables(assign, expression.filter, data):
        model.Add(variable == 0)


def _compile_exists(model, assign, expression, constraint_type, data):
    variables = _matching_variables(assign, expression.filter, data)
    count = sum(variables) if variables else 0
    if constraint_type == "hard":
        model.Add(count >= 1)
        return []
    penalty = model.NewIntVar(0, 1, "dynamic_exists_penalty")
    model.Add(penalty >= 1 - count)
    return [penalty]


def _compile_no_adjacent(model, assign, expression, constraint_type, data):
    penalties = []
    matching_set = set(_matching_variables(assign, expression.filter, data))
    by_teacher_day = {}

    for (class_id, subject_id, teacher_id, slot_id, room_id), variable in assign.items():
        if variable not in matching_set:
            continue
        day = data["slot_day"][slot_id]
        period = data["slot_period"][slot_id]
        by_teacher_day.setdefault((teacher_id, day), {}).setdefault(period, []).append(variable)

    for (teacher_id, day), periods in by_teacher_day.items():
        for period in sorted(periods):
            if period + 1 not in periods:
                continue
            current_sum = sum(periods[period])
            next_sum = sum(periods[period + 1])
            if constraint_type == "hard":
                model.Add(current_sum + next_sum <= 1)
            else:
                penalty = model.NewIntVar(0, 1, f"dynamic_consecutive_penalty_{teacher_id}_{day}_{period}")
                model.Add(penalty >= current_sum + next_sum - 1)
                penalties.append(penalty)
    return penalties


def _compare(actual, operator, expected):
    if operator == "eq": return actual == expected
    if operator == "neq": return actual != expected
    if operator == "lt": return actual < expected
    if operator == "lte": return actual <= expected
    if operator == "gt": return actual > expected
    if operator == "gte": return actual >= expected
    raise ValueError(f"Unsupported operator: {operator}")
