"""Business logic and SQL aggregate queries."""

from dataclasses import dataclass
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Grade, Student
from .repositories import GradeRepository


@dataclass(frozen=True)
class GradeStatistics:
    average: float
    minimum: int
    maximum: int


class GradingService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def statistics(self, student_id: int, subject_id: int | None = None) -> GradeStatistics | None:
        statement = select(
            func.avg(Grade.value), func.min(Grade.value), func.max(Grade.value)
        ).where(Grade.student_id == student_id)
        if subject_id is not None:
            statement = statement.where(Grade.subject_id == subject_id)
        average, minimum, maximum = self.session.execute(statement).one()
        if average is None:
            return None
        return GradeStatistics(
            round(float(cast(float, average)), 2),
            int(cast(int, minimum)),
            int(cast(int, maximum)),
        )

    def performance(self, student_id: int) -> str:
        stats = self.statistics(student_id)
        if stats is None:
            return "немає оцінок"
        if stats.average >= 10:
            return "відмінно"
        if stats.average >= 7:
            return "добре"
        if stats.average >= 4:
            return "задовільно"
        return "незадовільно"

    def ranking(self) -> list[tuple[Student, float]]:
        statement = (
            select(Student, func.avg(Grade.value).label("average"))
            .join(Grade)
            .group_by(Student.id)
            .order_by(func.avg(Grade.value).desc(), Student.full_name)
        )
        return [
            (cast(Student, student), round(float(cast(float, average)), 2))
            for student, average in self.session.execute(statement)
        ]

    def above_threshold(self, threshold: float) -> list[tuple[Student, float]]:
        statement = (
            select(Student, func.avg(Grade.value).label("average"))
            .join(Grade)
            .group_by(Student.id)
            .having(func.avg(Grade.value) > threshold)
            .order_by(func.avg(Grade.value).desc())
        )
        return [
            (cast(Student, student), round(float(cast(float, average)), 2))
            for student, average in self.session.execute(statement)
        ]


def assign_grades_transactionally(
    session: Session, rows: list[tuple[int, int, int, int, str]]
) -> list[Grade]:
    """Store all grades atomically; every invalid row causes a full rollback."""
    repository = GradeRepository(session)
    saved: list[Grade] = []
    try:
        for student_id, subject_id, value, semester, assessment_type in rows:
            if not 1 <= value <= 12:
                raise ValueError("Grade must be between 1 and 12")
            if semester < 1:
                raise ValueError("Semester must be positive")
            saved.append(
                repository.add(
                    student_id,
                    subject_id,
                    value,
                    semester=semester,
                    assessment_type=assessment_type,
                )
            )
        session.commit()
        return saved
    except Exception:
        session.rollback()
        raise
