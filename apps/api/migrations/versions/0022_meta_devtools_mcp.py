"""Meta webhook test history table.

Revision ID: 0022_meta_devtools_mcp
Revises: 0021_carousel_instagram_bridge
"""

from alembic import op
import sqlalchemy as sa


revision = "0022_meta_devtools_mcp"
down_revision = "0021_carousel_instagram_bridge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_webhook_tests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("test_id", sa.String(length=64), nullable=False),
        sa.Column("app_id", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("event_type", sa.String(length=80), nullable=False, server_default="messages"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="requested"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("test_id"),
    )
    op.create_index("ix_meta_webhook_tests_agency_id", "meta_webhook_tests", ["agency_id"])
    op.create_index("ix_meta_webhook_tests_test_id", "meta_webhook_tests", ["test_id"])


def downgrade() -> None:
    op.drop_table("meta_webhook_tests")
