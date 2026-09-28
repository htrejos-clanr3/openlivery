"""LinkedIn copy desk tables.

Revision ID: 0034_linkedin_desk
Revises: 0033_inbox_desk
"""

from alembic import op
import sqlalchemy as sa


revision = "0034_linkedin_desk"
down_revision = "0033_inbox_desk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "linkedin_channels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("profile_url", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("display_name", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("voice_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", name="uq_linkedin_channels_client_id"),
    )
    op.create_index("ix_linkedin_channels_agency_id", "linkedin_channels", ["agency_id"])
    op.create_index("ix_linkedin_channels_client_id", "linkedin_channels", ["client_id"])

    op.create_table(
        "linkedin_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False, server_default="post"),
        sa.Column("idea", sa.Text(), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("hook_id", sa.Integer(), nullable=True),
        sa.Column("human_score", sa.Float(), nullable=True),
        sa.Column("verdict", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["channel_id"], ["linkedin_channels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_linkedin_drafts_agency_id", "linkedin_drafts", ["agency_id"])
    op.create_index("ix_linkedin_drafts_channel_id", "linkedin_drafts", ["channel_id"])


def downgrade() -> None:
    op.drop_index("ix_linkedin_drafts_channel_id", table_name="linkedin_drafts")
    op.drop_index("ix_linkedin_drafts_agency_id", table_name="linkedin_drafts")
    op.drop_table("linkedin_drafts")
    op.drop_index("ix_linkedin_channels_client_id", table_name="linkedin_channels")
    op.drop_index("ix_linkedin_channels_agency_id", table_name="linkedin_channels")
    op.drop_table("linkedin_channels")
