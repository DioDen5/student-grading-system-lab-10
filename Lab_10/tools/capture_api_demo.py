"""Print a deterministic sequence of real API requests for report evidence."""

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from grade_service.api import create_app


def show(method: str, path: str, response) -> None:
    print(f"> {method} {path}")
    print(f"< {response.status_code} {response.json() if response.content else ''}")


with TemporaryDirectory() as folder:
    app = create_app(Path(folder) / "demo.db")
    with TestClient(app) as client:
        student = client.post("/students", json={"full_name": "Заставний Денис"})
        show("POST", "/students", student)
        subject = client.post("/subjects", json={"name": "Professional Python"})
        show("POST", "/subjects", subject)
        grade = client.post(
            "/grades",
            json={
                "student_id": 1,
                "subject_id": 1,
                "value": 12,
                "semester": 1,
                "assessment_type": "exam",
            },
        )
        show("POST", "/grades", grade)
        show("GET", "/students/1/average", client.get("/students/1/average"))
        show("GET", "/students?min_average=10", client.get("/students", params={"min_average": 10}))
