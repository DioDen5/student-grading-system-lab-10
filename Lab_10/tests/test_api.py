def create_entities(client):
    student = client.post("/students", json={"full_name": "Заставний Денис"})
    subject = client.post("/subjects", json={"name": "Professional Python"})
    assert student.status_code == 201
    assert subject.status_code == 201
    return student.json(), subject.json()


def create_grade(client, value=12, semester=1, assessment_type="exam"):
    student, subject = create_entities(client)
    response = client.post(
        "/grades",
        json={
            "student_id": student["id"],
            "subject_id": subject["id"],
            "value": value,
            "semester": semester,
            "assessment_type": assessment_type,
        },
    )
    return student, subject, response


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "environment": "development",
        "version": "1.0.0",
    }


def test_create_student_and_subject(client):
    student, subject = create_entities(client)
    assert student == {"id": 1, "full_name": "Заставний Денис"}
    assert subject == {"id": 1, "name": "Professional Python"}
    assert client.get("/subjects").json() == [subject]


def test_request_normalization(client):
    student = client.post("/students", json={"full_name": "  Денис   Заставний "})
    subject = client.post("/subjects", json={"name": "  Бази   даних "})
    assert student.json()["full_name"] == "Денис Заставний"
    assert subject.json()["name"] == "Бази даних"


def test_blank_names_are_rejected(client):
    assert client.post("/students", json={"full_name": "   "}).status_code == 422
    assert client.post("/subjects", json={"name": "   "}).status_code == 422


def test_duplicate_student_and_subject(client):
    create_entities(client)
    assert client.post("/students", json={"full_name": "Заставний Денис"}).status_code == 409
    assert client.post("/subjects", json={"name": "Professional Python"}).status_code == 409


def test_create_and_get_grades(client):
    student, _, response = create_grade(client)
    assert response.status_code == 201
    assert response.json()["value"] == 12
    grades = client.get(f"/students/{student['id']}/grades")
    assert grades.status_code == 200
    assert [item["value"] for item in grades.json()] == [12]
    assert [item["value"] for item in client.get("/grades").json()] == [12]


def test_grade_validation(client):
    student, subject = create_entities(client)
    response = client.post(
        "/grades", json={"student_id": student["id"], "subject_id": subject["id"], "value": 13}
    )
    assert response.status_code == 422


def test_invalid_student_and_subject_for_grade(client):
    assert (
        client.post("/grades", json={"student_id": 999, "subject_id": 999, "value": 10}).status_code
        == 404
    )
    student = client.post("/students", json={"full_name": "Денис"}).json()
    response = client.post(
        "/grades", json={"student_id": student["id"], "subject_id": 999, "value": 10}
    )
    assert response.status_code == 404


def test_duplicate_grade_returns_conflict(client):
    student, subject, first = create_grade(client)
    assert first.status_code == 201
    second = client.post(
        "/grades",
        json={"student_id": student["id"], "subject_id": subject["id"], "value": 9},
    )
    assert second.status_code == 409


def test_average_min_max_and_performance(client):
    student = client.post("/students", json={"full_name": "Заставний Денис"}).json()
    python = client.post("/subjects", json={"name": "Python"}).json()
    database = client.post("/subjects", json={"name": "Databases"}).json()
    for subject, value in [(python, 12), (database, 8)]:
        response = client.post(
            "/grades",
            json={"student_id": student["id"], "subject_id": subject["id"], "value": value},
        )
        assert response.status_code == 201
    response = client.get(f"/students/{student['id']}/average")
    assert response.status_code == 200
    assert response.json() == {
        "student_id": student["id"],
        "average": 10.0,
        "minimum": 8,
        "maximum": 12,
        "performance": "відмінно",
    }


def test_average_errors(client):
    assert client.get("/students/999/average").status_code == 404
    student = client.post("/students", json={"full_name": "Без оцінок"}).json()
    assert client.get(f"/students/{student['id']}/average").status_code == 404


def test_missing_student_grades(client):
    response = client.get("/students/999/grades")
    assert response.status_code == 404


def test_patch_and_delete_grade(client):
    _, _, created = create_grade(client, value=7)
    grade_id = created.json()["id"]
    updated = client.patch(f"/grades/{grade_id}", json={"value": 11})
    assert updated.status_code == 200
    assert updated.json()["value"] == 11
    deleted = client.delete(f"/grades/{grade_id}")
    assert deleted.status_code == 204
    assert client.delete(f"/grades/{grade_id}").status_code == 404


def test_patch_missing_and_invalid_grade(client):
    assert client.patch("/grades/999", json={"value": 10}).status_code == 404
    assert client.patch("/grades/999", json={"value": 0}).status_code == 422


def test_ranking_and_min_average_query(client):
    subject = client.post("/subjects", json={"name": "Python"}).json()
    for name, value in [("Заставний Денис", 12), ("Коваль Анна", 7)]:
        student = client.post("/students", json={"full_name": name}).json()
        client.post(
            "/grades",
            json={"student_id": student["id"], "subject_id": subject["id"], "value": value},
        )
    all_students = client.get("/students")
    assert [item["full_name"] for item in all_students.json()] == ["Заставний Денис", "Коваль Анна"]
    filtered = client.get("/students", params={"min_average": 8})
    assert [item["full_name"] for item in filtered.json()] == ["Заставний Денис"]
    assert client.get("/students", params={"min_average": 99}).status_code == 422


def test_openapi_documents_all_required_methods(client):
    schema = client.get("/openapi.json").json()
    assert {"post"} <= set(schema["paths"]["/students"])
    assert {"get", "post"} <= set(schema["paths"]["/subjects"])
    assert {"get", "post"} <= set(schema["paths"]["/grades"])
    assert {"patch", "delete"} <= set(schema["paths"]["/grades/{grade_id}"])
    assert {"get"} <= set(schema["paths"]["/students/{student_id}/average"])
