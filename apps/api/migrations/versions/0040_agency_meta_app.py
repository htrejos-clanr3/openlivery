"""Agency-level Meta app credentials.

Revision ID: 0040_agency_meta_app
Revises: 0039_products
"""

from alembic import op
import sqlalchemy as sa


revision = "0040_agency_meta_app"
down_revision = "0039_products"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agencies", sa.Column("meta_app_id", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("agencies", sa.Column("encrypted_meta_app_secret", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("agencies", "encrypted_meta_app_secret")
    op.drop_column("agencies", "meta_app_id")
