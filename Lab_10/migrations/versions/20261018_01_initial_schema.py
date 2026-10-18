"""Create students, subjects and grades tables.

Revision ID: 20261018_01
Revises: None
"""
from alembic import op
import sqlalchemy as sa

revision = "20261018_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(200), nullable=False, unique=True),
    )
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
    )
    op.create_table(
        "grades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("assessment_type", sa.String(50), nullable=False, server_default="exam"),
        sa.CheckConstraint("value BETWEEN 1 AND 12", name="ck_grades_value_1_12"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_grades_student_id", "grades", ["student_id"])
    op.create_index("ix_grades_subject_id", "grades", ["subject_id"])


def downgrade() -> None:
    op.drop_index("ix_grades_subject_id", table_name="grades")
    op.drop_index("ix_grades_student_id", table_name="grades")
    op.drop_table("grades")
    op.drop_table("subjects")
    op.drop_table("students")

