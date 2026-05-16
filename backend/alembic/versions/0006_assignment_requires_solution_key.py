"""assignment.requires_solution_key

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-15
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("assignment", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "requires_solution_key",
                sa.Boolean(),
                server_default="1",
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("assignment", schema=None) as batch_op:
        batch_op.drop_column("requires_solution_key")
