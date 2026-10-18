"""Add semester to grades.

Revision ID: 20261018_02
Revises: 20261018_01
"""
from alembic import op
import sqlalchemy as sa

revision = "20261018_02"
down_revision = "20261018_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("grades") as batch_op:
        batch_op.add_column(sa.Column("semester", sa.Integer(), nullable=False, server_default="1"))
        batch_op.create_unique_constraint(
            "uq_grade_assessment",
            ["student_id", "subject_id", "semester", "assessment_type"],
        )


def downgrade() -> None:
    with op.batch_alter_table("grades") as batch_op:
        batch_op.drop_constraint("uq_grade_assessment", type_="unique")
        batch_op.drop_column("semester")

