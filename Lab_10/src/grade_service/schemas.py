"""Pydantic request and response schemas for the REST API."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StudentCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)

    @field_validator("full_name")
    @classmethod
    def full_name_not_blank(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Full name must not be blank")
        return cleaned


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str


class SubjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Subject name must not be blank")
        return cleaned


class SubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class GradeCreate(BaseModel):
    student_id: int = Field(gt=0)
    subject_id: int = Field(gt=0)
    value: int = Field(ge=1, le=12)
    semester: int = Field(default=1, ge=1, le=20)
    assessment_type: str = Field(default="exam", min_length=2, max_length=50)


class GradeUpdate(BaseModel):
    value: int = Field(ge=1, le=12)


class GradeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    subject_id: int
    value: int
    semester: int
    assessment_type: str


class StatisticsRead(BaseModel):
    student_id: int
    average: float
    minimum: int
    maximum: int
    performance: str


class RankedStudentRead(BaseModel):
    id: int
    full_name: str
    average: float
