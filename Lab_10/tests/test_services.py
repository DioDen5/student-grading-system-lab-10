import pytest

from grade_service.repositories import GradeRepository, StudentRepository, SubjectRepository
from grade_service.services import GradingService, assign_grades_transactionally


def seeded(session):
    students = StudentRepository(session)
    subjects = SubjectRepository(session)
    first = students.add("Заставний Денис")
    second = students.add("Коваль Анна")
    python = subjects.add("Python")
    database = subjects.add("Databases")
    grades = GradeRepository(session)
    grades.add(first.id, python.id, 12, assessment_type="exam")
    grades.add(first.id, database.id, 10, assessment_type="exam")
    grades.add(second.id, python.id, 7, assessment_type="exam")
    grades.add(second.id, database.id, 5, assessment_type="exam")
    return first, second, python, database


def test_avg_min_max(session):
    first, _, _, _ = seeded(session)
    stats = GradingService(session).statistics(first.id)
    assert (stats.average, stats.minimum, stats.maximum) == (11.0, 10, 12)


def test_subject_statistics(session):
    first, _, python, _ = seeded(session)
    stats = GradingService(session).statistics(first.id, python.id)
    assert (stats.average, stats.minimum, stats.maximum) == (12.0, 12, 12)


def test_statistics_without_grades(session):
    student = StudentRepository(session).add("Без оцінок")
    service = GradingService(session)
    assert service.statistics(student.id) is None
    assert service.performance(student.id) == "немає оцінок"


@pytest.mark.parametrize(
    ("grade", "expected"),
    [(12, "відмінно"), (8, "добре"), (5, "задовільно"), (2, "незадовільно")],
)
def test_performance_levels(session, grade, expected):
    student = StudentRepository(session).add(f"Студент {grade}")
    subject = SubjectRepository(session).add(f"Предмет {grade}")
    GradeRepository(session).add(student.id, subject.id, grade)
    assert GradingService(session).performance(student.id) == expected


def test_ranking_sorted_by_average(session):
    first, second, _, _ = seeded(session)
    ranking = GradingService(session).ranking()
    assert [item[0].id for item in ranking] == [first.id, second.id]
    assert [item[1] for item in ranking] == [11.0, 6.0]


def test_above_threshold(session):
    first, _, _, _ = seeded(session)
    result = GradingService(session).above_threshold(8)
    assert [(student.id, average) for student, average in result] == [(first.id, 11.0)]


def test_transaction_commit(session):
    student = StudentRepository(session).add("Денис")
    subject = SubjectRepository(session).add("Python")
    saved = assign_grades_transactionally(
        session,
        [(student.id, subject.id, 11, 1, "exam"), (student.id, subject.id, 12, 2, "exam")],
    )
    assert [grade.value for grade in saved] == [11, 12]
    assert len(GradeRepository(session).get_all()) == 2


def test_transaction_rollback_on_invalid_grade(session):
    student = StudentRepository(session).add("Денис")
    subject = SubjectRepository(session).add("Python")
    session.commit()
    with pytest.raises(ValueError, match="between 1 and 12"):
        assign_grades_transactionally(
            session,
            [(student.id, subject.id, 10, 1, "exam"), (student.id, subject.id, 99, 2, "exam")],
        )
    assert GradeRepository(session).get_all() == []


def test_transaction_rollback_on_invalid_semester(session):
    student = StudentRepository(session).add("Денис")
    subject = SubjectRepository(session).add("Python")
    session.commit()
    with pytest.raises(ValueError, match="positive"):
        assign_grades_transactionally(session, [(student.id, subject.id, 10, 0, "exam")])
    assert GradeRepository(session).get_all() == []
