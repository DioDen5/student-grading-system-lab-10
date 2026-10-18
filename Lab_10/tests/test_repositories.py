import pytest
from sqlalchemy.exc import IntegrityError

from grade_service.repositories import GradeRepository, StudentRepository, SubjectRepository


def test_student_crud(session):
    repository = StudentRepository(session)
    student = repository.add("Заставний Денис")
    assert repository.get(student.id).full_name == "Заставний Денис"
    assert repository.update(student.id, "Заставний Денис Андрійович").full_name.endswith(
        "Андрійович"
    )
    assert len(repository.get_all()) == 1
    assert repository.delete(student.id) is True
    assert repository.get(student.id) is None
    assert repository.delete(9999) is False
    assert repository.update(9999, "Nobody") is None


def test_subject_crud(session):
    repository = SubjectRepository(session)
    subject = repository.add("Python")
    assert repository.get(subject.id).name == "Python"
    assert repository.update(subject.id, "Professional Python").name == "Professional Python"
    assert [item.name for item in repository.get_all()] == ["Professional Python"]
    assert repository.delete(subject.id) is True
    assert repository.delete(subject.id) is False
    assert repository.update(9999, "Nobody") is None


def test_grade_crud(session):
    student = StudentRepository(session).add("Денис")
    subject = SubjectRepository(session).add("Python")
    repository = GradeRepository(session)
    grade = repository.add(student.id, subject.id, 10, semester=2, assessment_type="module")
    assert repository.get(grade.id).value == 10
    assert repository.update(grade.id, 12).value == 12
    assert repository.for_student(student.id) == [grade]
    assert repository.get_all() == [grade]
    assert repository.delete(grade.id) is True
    assert repository.delete(grade.id) is False
    assert repository.update(9999, 7) is None


def test_grade_check_constraint(session):
    student = StudentRepository(session).add("Денис")
    subject = SubjectRepository(session).add("Python")
    with pytest.raises(IntegrityError):
        GradeRepository(session).add(student.id, subject.id, 13)
    session.rollback()


def test_unique_names_and_assessment(session):
    students = StudentRepository(session)
    students.add("Денис")
    with pytest.raises(IntegrityError):
        students.add("Денис")
    session.rollback()


def test_foreign_key_enforced(session):
    with pytest.raises(IntegrityError):
        GradeRepository(session).add(999, 999, 8)
    session.rollback()


def test_cascade_delete(session):
    student = StudentRepository(session).add("Денис")
    subject = SubjectRepository(session).add("Python")
    grades = GradeRepository(session)
    grades.add(student.id, subject.id, 11)
    StudentRepository(session).delete(student.id)
    assert grades.get_all() == []


def test_grade_add_many(session):
    student = StudentRepository(session).add("Денис")
    subject = SubjectRepository(session).add("Python")
    saved = GradeRepository(session).add_many(
        [(student.id, subject.id, 9, 1, "module"), (student.id, subject.id, 12, 2, "exam")]
    )
    assert [item.value for item in saved] == [9, 12]
