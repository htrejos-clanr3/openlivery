"""Inbox desk: assignee, labels, canned replies.

Revision ID: 0033_inbox_desk
Revises: 0032_carousel_format_playbook
"""

from alembic import op
import sqlalchemy as sa


revision = "0033_inbox_desk"
down_revision = "0032_carousel_format_playbook"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("assigned_user_id", sa.Uuid(), nullable=True))
    op.add_column(
        "conversations",
        sa.Column("labels", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.create_foreign_key(
        "fk_conversations_assigned_user_id",
        "conversations",
        "users",
        ["assigned_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_conversations_assigned_user_id", "conversations", ["assigned_user_id"])

    op.create_table(
        "canned_replies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("shortcode", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agency_id", "shortcode", name="uq_canned_replies_agency_shortcode"),
    )
    op.create_index("ix_canned_replies_agency_id", "canned_replies", ["agency_id"])


def downgrade() -> None:
    op.drop_index("ix_canned_replies_agency_id", table_name="canned_replies")
    op.drop_table("canned_replies")
    op.drop_index("ix_conversations_assigned_user_id", table_name="conversations")
    op.drop_constraint("fk_conversations_assigned_user_id", "conversations", type_="foreignkey")
    op.drop_column("conversations", "labels")
    op.drop_column("conversations", "assigned_user_id")
