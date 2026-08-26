"""Instagram channel + editorial content publishing tables.

Revision ID: 0020_instagram_publishing
Revises: 0019_carousels_pomelli
"""

from alembic import op
import sqlalchemy as sa


revision = "0020_instagram_publishing"
down_revision = "0019_carousels_pomelli"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "instagram_channels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="disconnected"),
        sa.Column("instagram_user_id", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("page_id", sa.String(length=80), nullable=True),
        sa.Column("username", sa.String(length=180), nullable=True),
        sa.Column("display_name", sa.String(length=180), nullable=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_scopes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("connection_mode", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", name="uq_instagram_channels_client_id"),
    )
    op.create_index("ix_instagram_channels_agency_id", "instagram_channels", ["agency_id"])
    op.create_index("ix_instagram_channels_client_id", "instagram_channels", ["client_id"])

    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("mime_type", sa.String(length=100), nullable=False, server_default="application/octet-stream"),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("file_data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_assets_agency_id", "media_assets", ["agency_id"])
    op.create_index("ix_media_assets_client_id", "media_assets", ["client_id"])

    op.create_table(
        "content_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("caption", sa.Text(), nullable=False, server_default=""),
        sa.Column("hashtags", sa.Text(), nullable=False, server_default=""),
        sa.Column("cta", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("content_type", sa.String(length=30), nullable=False, server_default="IMAGE"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="DRAFT"),
        sa.Column("timezone", sa.String(length=80), nullable=False, server_default="UTC"),
        sa.Column("ai_meta", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_items_agency_id", "content_items", ["agency_id"])
    op.create_index("ix_content_items_client_id", "content_items", ["client_id"])
    op.create_index("ix_content_items_content_type", "content_items", ["content_type"])
    op.create_index("ix_content_items_status", "content_items", ["status"])
    op.create_index("ix_content_items_created_by_user_id", "content_items", ["created_by_user_id"])

    op.create_table(
        "content_media",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_id", sa.Uuid(), nullable=False),
        sa.Column("media_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["content_id"], ["content_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_id", "position", name="uq_content_media_position"),
    )
    op.create_index("ix_content_media_content_id", "content_media", ["content_id"])
    op.create_index("ix_content_media_media_id", "content_media", ["media_id"])

    op.create_table(
        "publications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("content_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("channel", sa.String(length=40), nullable=False, server_default="instagram"),
        sa.Column("provider_account_id", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="DRAFT"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(length=80), nullable=False, server_default="UTC"),
        sa.Column("provider_publication_id", sa.String(length=120), nullable=True),
        sa.Column("provider_container_id", sa.String(length=120), nullable=True),
        sa.Column("provider_permalink", sa.String(length=500), nullable=True),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_class", sa.String(length=40), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["content_id"], ["content_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_publications_idempotency_key"),
    )
    op.create_index("ix_publications_agency_id", "publications", ["agency_id"])
    op.create_index("ix_publications_client_id", "publications", ["client_id"])
    op.create_index("ix_publications_content_id", "publications", ["content_id"])
    op.create_index("ix_publications_channel", "publications", ["channel"])
    op.create_index("ix_publications_status", "publications", ["status"])
    op.create_index("ix_publications_scheduled_at", "publications", ["scheduled_at"])


def downgrade() -> None:
    op.drop_table("publications")
    op.drop_table("content_media")
    op.drop_table("content_items")
    op.drop_table("media_assets")
    op.drop_table("instagram_channels")
