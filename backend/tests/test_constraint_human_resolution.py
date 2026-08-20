from ortools.sat.python import cp_model

from app.constraints.compiler import compile_constraint
from app.constraints.schemas import GeneratedConstraint
from app.constraints.resolver import resolve_subject, resolve_teacher
from app.models.models import Teacher, Subject, Class, Room, TimeSlot


class FakeObj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self):
        self.data = {
            Teacher: [FakeObj(teacher_id=1, teacher_name="Prof. Rahul Sharma")],
            Subject: [FakeObj(subject_id=2, subject_name="Database Management Systems", subject_type="theory")],
            Class: [FakeObj(class_id=3, class_name="CSE-A")],
            Room: [FakeObj(room_id=4, room_number="Lab 1", room_type="classroom")],
            TimeSlot: [FakeObj(slot_id=5, day="Monday", period_number=3)],
        }

    def query(self, model):
        return FakeQuery(self.data[model])


def test_human_teacher_name_is_resolved_for_compilation():
    db = FakeDB()
    assert resolve_teacher(db, "Rahul Sharma").teacher_id == 1

    model = cp_model.CpModel()
    variable = model.NewBoolVar("rahul_monday_p3")
    assign = {(3, 2, 1, 5, 4): variable}
    data = {
        "db": db,
        "slot_day": {5: "Monday"},
        "slot_period": {5: 3},
        "room_types": {4: "classroom"},
        "subject_types": {2: "theory"},
    }

    constraint = GeneratedConstraint.model_validate({
        "constraint_type": "hard",
        "weight": None,
        "expression": {
            "kind": "forbid",
            "filter": {
                "kind": "and",
                "conditions": [
                    {"kind": "atomic", "field": "teacher", "operator": "eq", "value": "Prof. Rahul Sharma"},
                    {"kind": "atomic", "field": "day", "operator": "eq", "value": "Monday"},
                    {"kind": "atomic", "field": "period", "operator": "eq", "value": 3},
                ],
            },
        },
        "explanation": "Prof. Rahul Sharma cannot teach Monday period 3.",
        "assumptions": [],
    })

    compile_constraint(model, assign, constraint, data)
    model.Add(variable == 1)

    assert cp_model.CpSolver().Solve(model) == cp_model.INFEASIBLE


def test_human_subject_name_is_resolved_for_compilation():
    db = FakeDB()
    assert resolve_subject(db, "DBMS").subject_id == 2
