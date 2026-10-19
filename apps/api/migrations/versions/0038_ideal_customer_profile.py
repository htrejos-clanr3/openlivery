"""Ideal customer profile per client.

Revision ID: 0038_ideal_customer_profile
Revises: 0037_carousel_multi_publish
"""

from alembic import op
import sqlalchemy as sa


revision = "0038_ideal_customer_profile"
down_revision = "0037_carousel_multi_publish"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ideal_customer_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sectors", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("cities", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("keywords", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("disqualifiers", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("size_min", sa.Integer(), nullable=True),
        sa.Column("size_max", sa.Integer(), nullable=True),
        sa.Column("hot_min", sa.Integer(), nullable=False, server_default="75"),
        sa.Column("warm_min", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("auto_qualify", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ideal_customer_profiles_agency_id", "ideal_customer_profiles", ["agency_id"])
    op.create_index(
        "ix_ideal_customer_profiles_client_id",
        "ideal_customer_profiles",
        ["client_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_ideal_customer_profiles_client_id", table_name="ideal_customer_profiles")
    op.drop_index("ix_ideal_customer_profiles_agency_id", table_name="ideal_customer_profiles")
    op.drop_table("ideal_customer_profiles")
