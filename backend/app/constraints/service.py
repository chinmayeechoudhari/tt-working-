from __future__ import annotations

from sqlalchemy.orm import Session
from ortools.sat.python import cp_model

from app.constraints.generator import ConstraintGenerator
from app.constraints.validator import validate_constraint
from app.constraints.compiler import compile_constraint
from app.constraints.schemas import GeneratedConstraint


class ConstraintService:
    def __init__(self):
        self.generator = ConstraintGenerator()

    def generate_and_validate(self, db: Session, user_text: str) -> GeneratedConstraint:
        constraint = self.generator.generate(user_text)
        validate_constraint(db, constraint)
        return constraint

    def compile(self, model: cp_model.CpModel, assign: dict, constraint: GeneratedConstraint, data: dict) -> list:
        penalties = compile_constraint(
            model=model,
            assign=assign,
            constraint=constraint,
            data=data,
        )
        # The compiler produces a unit violation penalty. Apply the declared
        # soft-constraint weight here so the objective respects user intent.
        if constraint.constraint_type == "soft" and constraint.weight not in (None, 1):
            return [penalty * constraint.weight for penalty in penalties]
        return penalties

    def generate_validate_and_compile(
        self,
        db: Session,
        model: cp_model.CpModel,
        assign: dict,
        data: dict,
        user_text: str,
    ) -> tuple[GeneratedConstraint, list]:
        constraint = self.generate_and_validate(db=db, user_text=user_text)
        penalties = self.compile(
            model=model,
            assign=assign,
            constraint=constraint,
            data=data,
        )
        return constraint, penalties
