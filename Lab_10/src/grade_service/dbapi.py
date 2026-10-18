"""A parameterized operation implemented with standard Python DB-API."""

import sqlite3
from pathlib import Path


def find_grades(
    database_path: str | Path, full_name: str, subject_name: str
) -> list[tuple[int, int, str]]:
    """Return value, semester and assessment type for one student/subject."""
    with sqlite3.connect(database_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT grades.value, grades.semester, grades.assessment_type
            FROM grades
            JOIN students ON students.id = grades.student_id
            JOIN subjects ON subjects.id = grades.subject_id
            WHERE students.full_name = ? AND subjects.name = ?
            ORDER BY grades.semester, grades.id
            """,
            (full_name, subject_name),
        )
        return cursor.fetchall()
