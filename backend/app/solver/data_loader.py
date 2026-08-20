from sqlalchemy.orm import Session
from app.models.models import (
    Class, Subject, Teacher, Room, TimeSlot,
    TeacherSubject, TeacherAvailability
)

def load_solver_data(db: Session) -> dict:
    """Load all scheduling data from DB into solver-friendly format."""
    classes = db.query(Class).all()
    subjects = db.query(Subject).all()
    teachers = db.query(Teacher).all()
    rooms = db.query(Room).all()
    slots = db.query(TimeSlot).all()
    ts_links = db.query(TeacherSubject).all()
    avail = db.query(TeacherAvailability).filter(TeacherAvailability.is_available == False).all()
    return {
        "db": db,
        "class_ids": [c.class_id for c in classes],
        "subject_map": {s.subject_id: s.class_id for s in subjects},
        "subject_periods": {s.subject_id: s.periods_per_week for s in subjects},
        "subject_types": {s.subject_id: s.subject_type for s in subjects},
        "teacher_ids": [t.teacher_id for t in teachers],
        "teacher_max_periods": {t.teacher_id: t.max_periods_per_day for t in teachers},
        "room_ids": [r.room_id for r in rooms],
        "room_types": {r.room_id: r.room_type for r in rooms},
        "slot_ids": [s.slot_id for s in slots],
        "slots_by_day": _group_slots_by_day(slots),
        "teacher_subjects": _build_teacher_subject_map(ts_links),
        "unavailable_pairs": {(a.teacher_id, a.slot_id) for a in avail},
        "lab_subjects": {s.subject_id for s in subjects if s.subject_type == "lab"},
        "lab_rooms": {r.room_id for r in rooms if r.room_type == "lab"},
        "slot_day": {s.slot_id: s.day for s in slots},
        "slot_period": {s.slot_id: s.period_number for s in slots},
    }

def _group_slots_by_day(slots) -> dict:
    result = {}
    for s in slots:
        result.setdefault(s.day, []).append(s)
    return {day: [s.slot_id for s in sorted(day_slots, key=lambda s: s.period_number)] for day, day_slots in result.items()}

def _build_teacher_subject_map(ts_links) -> dict:
    result = {}
    for link in ts_links:
        result.setdefault(link.teacher_id, []).append(link.subject_id)
    return result
