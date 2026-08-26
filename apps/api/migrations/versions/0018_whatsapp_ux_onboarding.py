"""WhatsApp Cloud UX: connection_mode for managed vs manual.

Revision ID: 0018_whatsapp_ux_onboarding
Revises: 0017_whatsapp_cloud_channel
"""

from alembic import op
import sqlalchemy as sa


revision = "0018_whatsapp_ux_onboarding"
down_revision = "0017_whatsapp_cloud_channel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "whatsapp_cloud_channels",
        sa.Column("connection_mode", sa.String(length=20), server_default="manual", nullable=False),
    )
    op.create_index(
        "ix_whatsapp_cloud_channels_phone_number_id",
        "whatsapp_cloud_channels",
        ["phone_number_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_whatsapp_cloud_channels_phone_number_id", table_name="whatsapp_cloud_channels")
    op.drop_column("whatsapp_cloud_channels", "connection_mode")
