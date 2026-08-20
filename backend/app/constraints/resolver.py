from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from sqlalchemy.orm import Session
from app.models.models import Teacher, Subject, Class, Room, TimeSlot


class EntityResolutionError(Exception):
    """Raised when a user-mentioned entity cannot be resolved."""
    pass


_TEACHER_TITLES = {"prof", "professor", "dr", "doctor", "mr", "mrs", "ms", "miss"}


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value)).strip().lower()
    value = re.sub(r"[\u2010-\u2015\-_/]+", " ", value)
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def _preserve_words(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value)).strip()
    value = re.sub(r"[\u2010-\u2015\-_/]+", " ", value)
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize(value))


def _teacher_normalize(value: str) -> str:
    tokens = [token for token in _normalize(value).split() if token not in _TEACHER_TITLES]
    return " ".join(tokens)


def _acronym(value: str) -> str:
    return "".join(token[0] for token in _normalize(value).split() if token)


def _is_subsequence(short: str, long: str) -> bool:
    if not short or len(short) > len(long):
        return False
    iterator = iter(long)
    return all(char in iterator for char in short)


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _compact(left), _compact(right)).ratio()


def _resolve_entity(values: list, query: str, *, label: str, display_attr: str, teacher: bool = False):
    query_normalized = _normalize(query)
    query_compact = _compact(query)
    query_teacher = _teacher_normalize(query) if teacher else query_normalized

    if not query_normalized:
        raise EntityResolutionError(f"{label} '{query}' was not found.")

    def name_of(item):
        return str(getattr(item, display_attr))

    matches = [item for item in values if _normalize(name_of(item)) == query_normalized]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(name_of(item) for item in matches[:5])
        raise EntityResolutionError(f"Multiple {label.lower()}s matched '{query}': {names}.")

    matches = [item for item in values if _compact(name_of(item)) == query_compact]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(name_of(item) for item in matches[:5])
        raise EntityResolutionError(f"Multiple {label.lower()}s matched '{query}': {names}.")

    if teacher:
        matches = [item for item in values if _teacher_normalize(name_of(item)) == query_teacher]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            names = ", ".join(name_of(item) for item in matches[:5])
            raise EntityResolutionError(f"Multiple {label.lower()}s matched '{query}': {names}.")

    query_tokens = set(query_teacher.split() if teacher else query_normalized.split())
    token_matches = []
    if query_tokens:
        for item in values:
            candidate = _teacher_normalize(name_of(item)) if teacher else _normalize(name_of(item))
            if query_tokens.issubset(set(candidate.split())):
                token_matches.append(item)
    if len(token_matches) == 1:
        return token_matches[0]
    if len(token_matches) > 1:
        names = ", ".join(name_of(item) for item in token_matches[:5])
        raise EntityResolutionError(f"Multiple {label.lower()}s matched '{query}': {names}.")

    acronym_matches = []
    for item in values:
        candidate = _compact(name_of(item))
        acronym = _acronym(name_of(item))
        if query_compact == acronym or (len(query_compact) >= 3 and _is_subsequence(query_compact, candidate)):
            acronym_matches.append(item)
    if len(acronym_matches) == 1:
        return acronym_matches[0]
    if len(acronym_matches) > 1:
        names = ", ".join(name_of(item) for item in acronym_matches[:5])
        raise EntityResolutionError(f"Multiple {label.lower()}s matched '{query}': {names}.")

    scored = sorted(((_similarity(query, name_of(item)), item) for item in values), key=lambda pair: pair[0], reverse=True)
    if scored and scored[0][0] >= 0.86:
        best_score = scored[0][0]
        close = [item for score, item in scored if best_score - score < 0.015]
        if len(close) == 1:
            return close[0]

    raise EntityResolutionError(f"{label} '{query}' was not found.")


def resolve_teacher(db: Session, name: str) -> Teacher:
    return _resolve_entity(db.query(Teacher).all(), name, label="Teacher", display_attr="teacher_name", teacher=True)


def resolve_subject(db: Session, name: str) -> Subject:
    return _resolve_entity(db.query(Subject).all(), name, label="Subject", display_attr="subject_name")


def resolve_subject_candidates(db: Session, name: str) -> list[Subject]:
    values = db.query(Subject).all()
    query_normalized = _normalize(name)
    query_compact = _compact(name)
    if not query_normalized:
        raise EntityResolutionError(f"Subject '{name}' was not found.")
    exact = [item for item in values if _normalize(item.subject_name) == query_normalized]
    if exact:
        return exact
    compact = [item for item in values if _compact(item.subject_name) == query_compact]
    if compact:
        return compact
    return [_resolve_entity(values, name, label="Subject", display_attr="subject_name")]


def resolve_subjects(db: Session, name: str) -> list[Subject]:
    return resolve_subject_candidates(db, name)


def resolve_class(db: Session, name: str) -> Class:
    text = str(name).strip()
    if text.isdigit():
        item = db.query(Class).filter(Class.class_id == int(text)).first()
        if item is not None:
            return item
    return _resolve_entity(db.query(Class).all(), text, label="Class", display_attr="class_name")


def resolve_room(db: Session, room_number: str) -> Room:
    query = re.sub(r"^room\s+", "", _normalize(room_number))
    rooms = db.query(Room).all()
    exact = [room for room in rooms if re.sub(r"^room\s+", "", _normalize(room.room_number)) == query]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise EntityResolutionError(f"Multiple rooms matched '{room_number}'.")
    return _resolve_entity(rooms, room_number, label="Room", display_attr="room_number")


def resolve_day_slots(db: Session, day: str) -> list[TimeSlot]:
    normalized = _normalize(day)
    matches = [slot for slot in db.query(TimeSlot).all() if _normalize(slot.day) == normalized]
    if not matches:
        raise EntityResolutionError(f"No time slots found for day '{day}'.")
    return sorted(matches, key=lambda slot: slot.period_number)


def resolve_slot(db: Session, day: str, period: int) -> TimeSlot:
    normalized = _normalize(day)
    matches = [slot for slot in db.query(TimeSlot).all() if _normalize(slot.day) == normalized and slot.period_number == period]
    if not matches:
        raise EntityResolutionError(f"No slot found for {day}, period {period}.")
    if len(matches) > 1:
        raise EntityResolutionError(f"Multiple slots found for {day}, period {period}.")
    return matches[0]


def resolve_period(db: Session, period: int) -> list[TimeSlot]:
    matches = [slot for slot in db.query(TimeSlot).all() if slot.period_number == period]
    if not matches:
        raise EntityResolutionError(f"Period '{period}' was not found.")
    return matches


def parse_slot_value(value) -> tuple[str, int]:
    if isinstance(value, dict):
        day = value.get("day")
        period = value.get("period", value.get("period_number"))
        if day is None or period is None:
            raise EntityResolutionError(f"Slot '{value}' must contain day and period.")
        try:
            return _preserve_words(day), int(period)
        except (TypeError, ValueError) as exc:
            raise EntityResolutionError(f"Slot '{value}' has an invalid period.") from exc

    text = _preserve_words(str(value))
    match = re.fullmatch(r"(.+?)\s+(?:p|P|period|Period)\s*(\d+)", text, flags=re.IGNORECASE)
    if not match:
        raise EntityResolutionError(f"Could not understand slot '{value}'. Use a form such as 'Monday Period 3'.")
    return match.group(1), int(match.group(2))
