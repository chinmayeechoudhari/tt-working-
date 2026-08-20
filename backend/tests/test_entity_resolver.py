import pytest

from app.constraints.resolver import (
    EntityResolutionError,
    resolve_teacher,
    resolve_subject,
    resolve_class,
    resolve_room,
    resolve_day_slots,
    resolve_slot,
    resolve_period,
    parse_slot_value,
)
from app.models.models import Teacher, Subject, Class, Room, TimeSlot


class FakeTeacher:
    def __init__(self, teacher_id, teacher_name):
        self.teacher_id = teacher_id
        self.teacher_name = teacher_name


class FakeSubject:
    def __init__(self, subject_id, subject_name):
        self.subject_id = subject_id
        self.subject_name = subject_name


class FakeClass:
    def __init__(self, class_id, class_name):
        self.class_id = class_id
        self.class_name = class_name


class FakeRoom:
    def __init__(self, room_id, room_number):
        self.room_id = room_id
        self.room_number = room_number


class FakeSlot:
    def __init__(self, slot_id, day, period_number):
        self.slot_id = slot_id
        self.day = day
        self.period_number = period_number


class FakeQuery:
    def __init__(self, data):
        self.data = data

    def all(self):
        return self.data


class FakeDB:
    def __init__(self, teachers=None, subjects=None, classes=None, rooms=None, slots=None):
        self.data = {
            Teacher: teachers or [],
            Subject: subjects or [],
            Class: classes or [],
            Room: rooms or [],
            TimeSlot: slots or [],
        }

    def query(self, model):
        return FakeQuery(self.data[model])


def test_resolve_teacher_case_insensitive():
    db = FakeDB(teachers=[FakeTeacher(1, "Rahul")])
    teacher = resolve_teacher(db, " rahul ")
    assert teacher.teacher_id == 1


def test_resolve_teacher_ignores_title_and_punctuation():
    db = FakeDB(teachers=[FakeTeacher(1, "Prof. Rahul Sharma")])
    assert resolve_teacher(db, "rahul sharma").teacher_id == 1
    assert resolve_teacher(db, "Prof Rahul Sharma").teacher_id == 1


def test_resolve_teacher_by_unique_last_name():
    db = FakeDB(teachers=[FakeTeacher(1, "Prof. Rahul Sharma")])
    assert resolve_teacher(db, "Sharma").teacher_id == 1


def test_resolve_teacher_rejects_ambiguous_token():
    db = FakeDB(teachers=[
        FakeTeacher(1, "Rahul Sharma"),
        FakeTeacher(2, "Amit Sharma"),
    ])
    with pytest.raises(EntityResolutionError, match="Multiple"):
        resolve_teacher(db, "Sharma")


def test_resolve_teacher_high_confidence_typo():
    db = FakeDB(teachers=[FakeTeacher(1, "Rahul Sharma")])
    assert resolve_teacher(db, "Rahul Sharm").teacher_id == 1


def test_unknown_teacher():
    db = FakeDB(teachers=[FakeTeacher(1, "Rahul")])
    with pytest.raises(EntityResolutionError):
        resolve_teacher(db, "Amit")


def test_resolve_subject():
    db = FakeDB(subjects=[FakeSubject(3, "DBMS")])
    assert resolve_subject(db, "dbms").subject_id == 3


def test_resolve_subject_by_acronym():
    db = FakeDB(subjects=[FakeSubject(3, "Database Management Systems")])
    assert resolve_subject(db, "DBMS").subject_id == 3


def test_resolve_class_ignores_hyphen_spacing():
    db = FakeDB(classes=[FakeClass(2, "CSE-A")])
    assert resolve_class(db, "cse a").class_id == 2


def test_resolve_room_allows_room_prefix():
    db = FakeDB(rooms=[FakeRoom(5, "Lab 1")])
    assert resolve_room(db, "Room Lab 1").room_id == 5
    assert resolve_room(db, "LAB 1").room_id == 5


def test_resolve_day_slots_sorted():
    db = FakeDB(slots=[
        FakeSlot(3, "Monday", 3),
        FakeSlot(1, "Monday", 1),
        FakeSlot(2, "Monday", 2),
    ])
    slots = resolve_day_slots(db, "monday")
    assert [slot.slot_id for slot in slots] == [1, 2, 3]


def test_resolve_specific_slot():
    db = FakeDB(slots=[
        FakeSlot(1, "Monday", 1),
        FakeSlot(2, "Monday", 2),
    ])
    assert resolve_slot(db, "Monday", 2).slot_id == 2


def test_parse_text_slot():
    assert parse_slot_value("Monday Period 3") == ("Monday", 3)
    assert parse_slot_value("Monday P3") == ("Monday", 3)


def test_parse_structured_slot():
    assert parse_slot_value({"day": "Tuesday", "period": 4}) == ("Tuesday", 4)


def test_resolve_period():
    db = FakeDB(slots=[
        FakeSlot(1, "Monday", 2),
        FakeSlot(2, "Tuesday", 2),
    ])
    assert {slot.slot_id for slot in resolve_period(db, 2)} == {1, 2}


def test_unknown_slot_is_rejected():
    db = FakeDB(slots=[FakeSlot(1, "Monday", 1)])
    with pytest.raises(EntityResolutionError):
        resolve_slot(db, "Monday", 9)
