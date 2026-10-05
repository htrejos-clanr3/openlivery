"""LinkedIn personal-profile OAuth and text publishing.

Revision ID: 0035_linkedin_oauth_publish
Revises: 0034_linkedin_desk
"""

from alembic import op
import sqlalchemy as sa


revision = "0035_linkedin_oauth_publish"
down_revision = "0034_linkedin_desk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "linkedin_channels",
        sa.Column("status", sa.String(length=30), nullable=False, server_default="disconnected"),
    )
    op.add_column(
        "linkedin_channels",
        sa.Column("member_id", sa.String(length=180), nullable=False, server_default=""),
    )
    op.add_column("linkedin_channels", sa.Column("encrypted_access_token", sa.Text(), nullable=True))
    op.add_column(
        "linkedin_channels",
        sa.Column("granted_scopes", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column("linkedin_channels", sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "linkedin_channels",
        sa.Column("connection_mode", sa.String(length=30), nullable=False, server_default="copy_paste"),
    )
    op.add_column("linkedin_channels", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("linkedin_channels", sa.Column("last_connected_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column(
        "linkedin_drafts",
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
    )
    op.add_column("linkedin_drafts", sa.Column("provider_post_id", sa.String(length=300), nullable=True))
    op.add_column("linkedin_drafts", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("linkedin_drafts", "published_at")
    op.drop_column("linkedin_drafts", "provider_post_id")
    op.drop_column("linkedin_drafts", "status")
    op.drop_column("linkedin_channels", "last_connected_at")
    op.drop_column("linkedin_channels", "last_error")
    op.drop_column("linkedin_channels", "connection_mode")
    op.drop_column("linkedin_channels", "token_expires_at")
    op.drop_column("linkedin_channels", "granted_scopes")
    op.drop_column("linkedin_channels", "encrypted_access_token")
    op.drop_column("linkedin_channels", "member_id")
    op.drop_column("linkedin_channels", "status")
