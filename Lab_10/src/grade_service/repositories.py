"""Repository layer that isolates persistence from business rules."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Grade, Student, Subject


class StudentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, full_name: str) -> Student:
        student = Student(full_name=full_name.strip())
        self.session.add(student)
        self.session.flush()
        return student

    def get(self, student_id: int) -> Student | None:
        return self.session.get(Student, student_id)

    def get_all(self) -> list[Student]:
        return list(self.session.scalars(select(Student).order_by(Student.full_name)))

    def update(self, student_id: int, full_name: str) -> Student | None:
        student = self.get(student_id)
        if student is not None:
            student.full_name = full_name.strip()
            self.session.flush()
        return student

    def delete(self, student_id: int) -> bool:
        student = self.get(student_id)
        if student is None:
            return False
        self.session.delete(student)
        self.session.flush()
        return True


class SubjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, name: str) -> Subject:
        subject = Subject(name=name.strip())
        self.session.add(subject)
        self.session.flush()
        return subject

    def get(self, subject_id: int) -> Subject | None:
        return self.session.get(Subject, subject_id)

    def get_all(self) -> list[Subject]:
        return list(self.session.scalars(select(Subject).order_by(Subject.name)))

    def update(self, subject_id: int, name: str) -> Subject | None:
        subject = self.get(subject_id)
        if subject is not None:
            subject.name = name.strip()
            self.session.flush()
        return subject

    def delete(self, subject_id: int) -> bool:
        subject = self.get(subject_id)
        if subject is None:
            return False
        self.session.delete(subject)
        self.session.flush()
        return True


class GradeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        student_id: int,
        subject_id: int,
        value: int,
        *,
        semester: int = 1,
        assessment_type: str = "exam",
    ) -> Grade:
        grade = Grade(
            student_id=student_id,
            subject_id=subject_id,
            value=value,
            semester=semester,
            assessment_type=assessment_type,
        )
        self.session.add(grade)
        self.session.flush()
        return grade

    def get(self, grade_id: int) -> Grade | None:
        return self.session.get(Grade, grade_id)

    def get_all(self) -> list[Grade]:
        return list(self.session.scalars(select(Grade).order_by(Grade.id)))

    def update(self, grade_id: int, value: int) -> Grade | None:
        grade = self.get(grade_id)
        if grade is not None:
            grade.value = value
            self.session.flush()
        return grade

    def delete(self, grade_id: int) -> bool:
        grade = self.get(grade_id)
        if grade is None:
            return False
        self.session.delete(grade)
        self.session.flush()
        return True

    def for_student(self, student_id: int) -> list[Grade]:
        statement = select(Grade).where(Grade.student_id == student_id).order_by(Grade.id)
        return list(self.session.scalars(statement))

    def add_many(self, rows: Sequence[tuple[int, int, int, int, str]]) -> list[Grade]:
        return [
            self.add(sid, subid, value, semester=semester, assessment_type=kind)
            for sid, subid, value, semester, kind in rows
        ]
