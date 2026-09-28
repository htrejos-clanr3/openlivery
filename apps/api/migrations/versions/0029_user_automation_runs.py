"""Per-user DeepSeek automation run history.

Revision ID: 0029_user_automation_runs
Revises: 0028_facebook_page_channel
"""

from alembic import op
import sqlalchemy as sa


revision = "0029_user_automation_runs"
down_revision = "0028_facebook_page_channel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_automation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("result", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_automation_runs_agency_id", "user_automation_runs", ["agency_id"])
    op.create_index("ix_user_automation_runs_user_id", "user_automation_runs", ["user_id"])
    op.create_index("ix_user_automation_runs_kind", "user_automation_runs", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_user_automation_runs_kind", table_name="user_automation_runs")
    op.drop_index("ix_user_automation_runs_user_id", table_name="user_automation_runs")
    op.drop_index("ix_user_automation_runs_agency_id", table_name="user_automation_runs")
    op.drop_table("user_automation_runs")
