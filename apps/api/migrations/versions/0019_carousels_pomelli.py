"""Carousels Pomelli: brand DNA, OAuth accounts, password reset, carousels.

Revision ID: 0019_carousels_pomelli
Revises: 0018_whatsapp_ux_onboarding

Idempotent where objects may already exist on long-lived local DBs.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0019_carousels_pomelli"
down_revision = "0018_whatsapp_ux_onboarding"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {col["name"] for col in inspect(bind).get_columns(table)}


def upgrade() -> None:
    # Google / passwordless agency users.
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=True)

    if not _has_column("clients", "brand_primary_color"):
        op.add_column("clients", sa.Column("brand_primary_color", sa.String(length=20), server_default="#075985", nullable=False))
    if not _has_column("clients", "brand_secondary_color"):
        op.add_column("clients", sa.Column("brand_secondary_color", sa.String(length=20), server_default="#0f172a", nullable=False))
    if not _has_column("clients", "brand_font"):
        op.add_column("clients", sa.Column("brand_font", sa.String(length=80), server_default="", nullable=False))
    if not _has_column("clients", "brand_voice"):
        op.add_column("clients", sa.Column("brand_voice", sa.Text(), server_default="", nullable=False))
    if not _has_column("clients", "brand_logo_data"):
        op.add_column("clients", sa.Column("brand_logo_data", sa.LargeBinary(), nullable=True))
    if not _has_column("clients", "brand_logo_mime"):
        op.add_column("clients", sa.Column("brand_logo_mime", sa.String(length=100), nullable=True))

    # portal_users may already exist from white-label portal migrations.
    if not _has_table("portal_users"):
        op.create_table(
            "portal_users",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("client_id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("client_id", "email", name="uq_portal_users_client_email"),
        )
        op.create_index("ix_portal_users_client_id", "portal_users", ["client_id"])
        op.create_index("ix_portal_users_email", "portal_users", ["email"])
    elif _has_column("portal_users", "password_hash"):
        # Allow Google-only portal users when the column already exists.
        op.alter_column("portal_users", "password_hash", existing_type=sa.String(length=255), nullable=True)

    if not _has_table("oauth_accounts"):
        op.create_table(
            "oauth_accounts",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("provider", sa.String(length=30), nullable=False),
            sa.Column("subject", sa.String(length=255), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=True),
            sa.Column("portal_user_id", sa.Uuid(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["portal_user_id"], ["portal_users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("provider", "subject", name="uq_oauth_provider_subject"),
        )
        op.create_index("ix_oauth_accounts_subject", "oauth_accounts", ["subject"])
        op.create_index("ix_oauth_accounts_email", "oauth_accounts", ["email"])
        op.create_index("ix_oauth_accounts_user_id", "oauth_accounts", ["user_id"])
        op.create_index("ix_oauth_accounts_portal_user_id", "oauth_accounts", ["portal_user_id"])

    if not _has_table("password_reset_tokens"):
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("audience", sa.String(length=20), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=True),
            sa.Column("portal_user_id", sa.Uuid(), nullable=True),
            sa.Column("purpose", sa.String(length=20), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["portal_user_id"], ["portal_users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
        )
        op.create_index("ix_password_reset_tokens_email", "password_reset_tokens", ["email"])
        op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"])

    if not _has_table("carousels"):
        op.create_table(
            "carousels",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("agency_id", sa.Uuid(), nullable=False),
            sa.Column("client_id", sa.Uuid(), nullable=False),
            sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
            sa.Column("approved_by_portal_user_id", sa.Uuid(), nullable=True),
            sa.Column("title", sa.String(length=180), nullable=False),
            sa.Column("brief", sa.Text(), nullable=False),
            sa.Column("caption", sa.Text(), nullable=False),
            sa.Column("language", sa.String(length=10), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("slide_count", sa.Integer(), nullable=False),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ig_media_id", sa.String(length=120), nullable=True),
            sa.Column("publish_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["approved_by_portal_user_id"], ["portal_users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_carousels_agency_id", "carousels", ["agency_id"])
        op.create_index("ix_carousels_client_id", "carousels", ["client_id"])
        op.create_index("ix_carousels_status", "carousels", ["status"])

    if not _has_table("carousel_slides"):
        op.create_table(
            "carousel_slides",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("carousel_id", sa.Uuid(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("headline", sa.String(length=240), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("cta", sa.String(length=180), nullable=False),
            sa.Column("layout_json", sa.JSON(), nullable=False),
            sa.Column("image_data", sa.LargeBinary(), nullable=True),
            sa.Column("image_mime", sa.String(length=100), nullable=True),
            sa.Column("agency_status", sa.String(length=30), nullable=False),
            sa.Column("client_status", sa.String(length=30), nullable=False),
            sa.Column("client_comment", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["carousel_id"], ["carousels.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("carousel_id", "position", name="uq_carousel_slides_position"),
        )
        op.create_index("ix_carousel_slides_carousel_id", "carousel_slides", ["carousel_id"])

    if not _has_table("carousel_events"):
        op.create_table(
            "carousel_events",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("carousel_id", sa.Uuid(), nullable=False),
            sa.Column("actor_type", sa.String(length=30), nullable=False),
            sa.Column("actor_id", sa.Uuid(), nullable=True),
            sa.Column("action", sa.String(length=80), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["carousel_id"], ["carousels.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_carousel_events_carousel_id", "carousel_events", ["carousel_id"])

    # Seed portal_users from legacy single portal credential when present.
    if _has_table("portal_users") and _has_column("clients", "portal_email"):
        op.execute(
            """
            INSERT INTO portal_users (id, client_id, name, email, password_hash, is_active, created_at)
            SELECT gen_random_uuid(), id, name, lower(portal_email), portal_password_hash, true, NOW()
            FROM clients
            WHERE portal_email IS NOT NULL AND portal_password_hash IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM portal_users pu
                WHERE pu.client_id = clients.id AND pu.email = lower(clients.portal_email)
              )
            """
        )


def downgrade() -> None:
    if _has_table("carousel_events"):
        op.drop_table("carousel_events")
    if _has_table("carousel_slides"):
        op.drop_table("carousel_slides")
    if _has_table("carousels"):
        op.drop_table("carousels")
    if _has_table("password_reset_tokens"):
        op.drop_table("password_reset_tokens")
    if _has_table("oauth_accounts"):
        op.drop_table("oauth_accounts")
    # Do not drop portal_users on downgrade: it may predate this revision.
    for column in (
        "brand_logo_mime",
        "brand_logo_data",
        "brand_voice",
        "brand_font",
        "brand_secondary_color",
        "brand_primary_color",
    ):
        if _has_column("clients", column):
            op.drop_column("clients", column)
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)
