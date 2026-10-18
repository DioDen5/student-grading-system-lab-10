from grade_service.dbapi import find_grades
from grade_service.repositories import GradeRepository, StudentRepository, SubjectRepository


def test_parameterized_dbapi_query(session, engine):
    student = StudentRepository(session).add("Заставний Денис")
    subject = SubjectRepository(session).add("Professional Python")
    GradeRepository(session).add(student.id, subject.id, 12, semester=2, assessment_type="exam")
    session.commit()
    assert find_grades(engine.url.database, "Заставний Денис", "Professional Python") == [
        (12, 2, "exam")
    ]


def test_dbapi_query_is_sql_injection_safe(session, engine):
    student = StudentRepository(session).add("Заставний Денис")
    subject = SubjectRepository(session).add("Python")
    GradeRepository(session).add(student.id, subject.id, 11)
    session.commit()
    assert find_grades(engine.url.database, "' OR 1=1 --", "Python") == []
