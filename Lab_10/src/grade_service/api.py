"""FastAPI application for variant 7."""

import logging
from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .database import create_schema, create_sqlite_engine, make_session_factory
from .logging_config import configure_logging
from .repositories import GradeRepository, StudentRepository, SubjectRepository
from .schemas import (
    GradeCreate,
    GradeRead,
    GradeUpdate,
    RankedStudentRead,
    StatisticsRead,
    StudentCreate,
    StudentRead,
    SubjectCreate,
    SubjectRead,
)
from .services import GradingService

logger = logging.getLogger(__name__)


def create_app(database: str | Path | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    engine = create_sqlite_engine(database if database is not None else settings.database_url)
    create_schema(engine)
    factory = make_session_factory(engine)
    application = FastAPI(
        title=settings.app_name,
        description="Lab_10, variant 7 — Заставний Денис, ФеП-32",
        version="1.0.0",
    )
    application.state.session_factory = factory
    application.state.engine = engine
    application.state.settings = settings
    logger.info("Grade Service started in %s environment", settings.environment)

    def get_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    @application.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment, "version": "1.0.0"}

    @application.get("/subjects", response_model=list[SubjectRead], tags=["subjects"])
    async def list_subjects(session: Session = Depends(get_session)) -> list[SubjectRead]:
        return [SubjectRead.model_validate(item) for item in SubjectRepository(session).get_all()]

    @application.get("/grades", response_model=list[GradeRead], tags=["grades"])
    async def list_grades(session: Session = Depends(get_session)) -> list[GradeRead]:
        return [GradeRead.model_validate(item) for item in GradeRepository(session).get_all()]

    @application.post(
        "/students",
        response_model=StudentRead,
        status_code=status.HTTP_201_CREATED,
        tags=["students"],
    )
    async def create_student(
        payload: StudentCreate, session: Session = Depends(get_session)
    ) -> StudentRead:
        try:
            student = StudentRepository(session).add(payload.full_name)
            session.commit()
            return StudentRead.model_validate(student)
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail="Student already exists") from exc

    @application.post(
        "/subjects",
        response_model=SubjectRead,
        status_code=status.HTTP_201_CREATED,
        tags=["subjects"],
    )
    async def create_subject(
        payload: SubjectCreate, session: Session = Depends(get_session)
    ) -> SubjectRead:
        try:
            subject = SubjectRepository(session).add(payload.name)
            session.commit()
            return SubjectRead.model_validate(subject)
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail="Subject already exists") from exc

    @application.post(
        "/grades", response_model=GradeRead, status_code=status.HTTP_201_CREATED, tags=["grades"]
    )
    async def create_grade(
        payload: GradeCreate, session: Session = Depends(get_session)
    ) -> GradeRead:
        if StudentRepository(session).get(payload.student_id) is None:
            raise HTTPException(status_code=404, detail="Student not found")
        if SubjectRepository(session).get(payload.subject_id) is None:
            raise HTTPException(status_code=404, detail="Subject not found")
        try:
            grade = GradeRepository(session).add(**payload.model_dump())
            session.commit()
            return GradeRead.model_validate(grade)
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail="Grade already exists") from exc

    @application.get(
        "/students/{student_id}/grades", response_model=list[GradeRead], tags=["students", "grades"]
    )
    async def student_grades(
        student_id: int, session: Session = Depends(get_session)
    ) -> list[GradeRead]:
        if StudentRepository(session).get(student_id) is None:
            raise HTTPException(status_code=404, detail="Student not found")
        return [
            GradeRead.model_validate(item)
            for item in GradeRepository(session).for_student(student_id)
        ]

    @application.get(
        "/students/{student_id}/average", response_model=StatisticsRead, tags=["students"]
    )
    async def student_average(
        student_id: int, session: Session = Depends(get_session)
    ) -> StatisticsRead:
        if StudentRepository(session).get(student_id) is None:
            raise HTTPException(status_code=404, detail="Student not found")
        service = GradingService(session)
        statistics = service.statistics(student_id)
        if statistics is None:
            raise HTTPException(status_code=404, detail="Student has no grades")
        return StatisticsRead(
            student_id=student_id,
            average=statistics.average,
            minimum=statistics.minimum,
            maximum=statistics.maximum,
            performance=service.performance(student_id),
        )

    @application.patch("/grades/{grade_id}", response_model=GradeRead, tags=["grades"])
    async def update_grade(
        grade_id: int, payload: GradeUpdate, session: Session = Depends(get_session)
    ) -> GradeRead:
        grade = GradeRepository(session).update(grade_id, payload.value)
        if grade is None:
            raise HTTPException(status_code=404, detail="Grade not found")
        session.commit()
        return GradeRead.model_validate(grade)

    @application.delete(
        "/grades/{grade_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["grades"]
    )
    async def delete_grade(grade_id: int, session: Session = Depends(get_session)) -> Response:
        if not GradeRepository(session).delete(grade_id):
            raise HTTPException(status_code=404, detail="Grade not found")
        session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.get("/students", response_model=list[RankedStudentRead], tags=["students"])
    async def students_by_average(
        min_average: float | None = Query(default=None, ge=1, le=12),
        session: Session = Depends(get_session),
    ) -> list[RankedStudentRead]:
        service = GradingService(session)
        rows = service.ranking() if min_average is None else service.above_threshold(min_average)
        return [
            RankedStudentRead(id=student.id, full_name=student.full_name, average=average)
            for student, average in rows
        ]

    return application


app = create_app()
