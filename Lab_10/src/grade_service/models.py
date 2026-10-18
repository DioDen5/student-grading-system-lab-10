"""SQLAlchemy ORM models."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    grades: Mapped[list[Grade]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    grades: Mapped[list[Grade]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )


class Grade(Base):
    __tablename__ = "grades"
    __table_args__ = (
        CheckConstraint("value BETWEEN 1 AND 12", name="ck_grades_value_1_12"),
        UniqueConstraint(
            "student_id",
            "subject_id",
            "semester",
            "assessment_type",
            name="uq_grade_assessment",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    value: Mapped[int] = mapped_column(nullable=False)
    semester: Mapped[int] = mapped_column(default=1, nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(50), default="exam", nullable=False)

    student: Mapped[Student] = relationship(back_populates="grades")
    subject: Mapped[Subject] = relationship(back_populates="grades")
