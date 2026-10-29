"""Content, approvals and provider connections.

Revision ID: 0041_marketing_foundation
Revises: 0040_agency_meta_app
"""

from alembic import op
import sqlalchemy as sa

revision = "0041_marketing_foundation"
down_revision = "0040_agency_meta_app"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_phones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("label", sa.String(120), nullable=False, server_default=""),
        sa.Column("can_approve", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_client_phones_client_id", "client_phones", ["client_id"])
    op.create_index("ix_client_phones_phone", "client_phones", ["phone"])

    op.create_table(
        "approval_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_approval_links_agency_id", "approval_links", ["agency_id"])
    op.create_index("ix_approval_links_client_id", "approval_links", ["client_id"])

    op.create_table(
        "post_pieces",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False, server_default=""),
        sa.Column("network", sa.String(32), nullable=False, server_default="instagram"),
        sa.Column("format", sa.String(32), nullable=False, server_default="image"),
        sa.Column("caption", sa.Text(), nullable=False, server_default=""),
        sa.Column("media_urls", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("publish_mode", sa.String(16), nullable=False, server_default="scheduled"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/Bogota"),
        sa.Column("approved_phone", sa.String(32), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_id", sa.String(120), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_post_pieces_agency_id", "post_pieces", ["agency_id"])
    op.create_index("ix_post_pieces_client_id", "post_pieces", ["client_id"])
    op.create_index("ix_post_pieces_status", "post_pieces", ["status"])

    op.create_table(
        "provider_connections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=True),
        sa.Column("provider", sa.String(48), nullable=False, server_default="higgsfield"),
        sa.Column("url", sa.String(400), nullable=False, server_default=""),
        sa.Column("auth_type", sa.String(24), nullable=False, server_default="api_key"),
        sa.Column("encrypted_secret", sa.Text(), nullable=True),
        sa.Column("billing_mode", sa.String(16), nullable=False, server_default="agency"),
        sa.Column("status", sa.String(24), nullable=False, server_default="unverified"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_provider_connections_agency_id", "provider_connections", ["agency_id"])
    op.create_index("ix_provider_connections_client_id", "provider_connections", ["client_id"])


def downgrade() -> None:
    op.drop_table("provider_connections")
    op.drop_table("post_pieces")
    op.drop_table("approval_links")
    op.drop_table("client_phones")
