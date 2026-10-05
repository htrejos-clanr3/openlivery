"""Legal acceptance audit log.

Revision ID: 0028_legal_acceptances
Revises: 0027_slide_product_image
"""

from alembic import op
import sqlalchemy as sa


revision = "0028_legal_acceptances"
down_revision = "0027_slide_product_image"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legal_acceptances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=True),
        sa.Column("acceptance_type", sa.String(length=40), nullable=False),
        sa.Column("document_key", sa.String(length=80), nullable=False),
        sa.Column("document_version", sa.String(length=40), server_default="", nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=True),
        sa.Column("metadata_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_legal_acceptances_agency_id", "legal_acceptances", ["agency_id"])
    op.create_index("ix_legal_acceptances_user_id", "legal_acceptances", ["user_id"])
    op.create_index("ix_legal_acceptances_client_id", "legal_acceptances", ["client_id"])
    op.create_index("ix_legal_acceptances_acceptance_type", "legal_acceptances", ["acceptance_type"])
    op.create_index("ix_legal_acceptances_document_key", "legal_acceptances", ["document_key"])
    op.create_index("ix_legal_acceptances_channel", "legal_acceptances", ["channel"])
    op.create_index("ix_legal_acceptances_created_at", "legal_acceptances", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_legal_acceptances_created_at", table_name="legal_acceptances")
    op.drop_index("ix_legal_acceptances_channel", table_name="legal_acceptances")
    op.drop_index("ix_legal_acceptances_document_key", table_name="legal_acceptances")
    op.drop_index("ix_legal_acceptances_acceptance_type", table_name="legal_acceptances")
    op.drop_index("ix_legal_acceptances_client_id", table_name="legal_acceptances")
    op.drop_index("ix_legal_acceptances_user_id", table_name="legal_acceptances")
    op.drop_index("ix_legal_acceptances_agency_id", table_name="legal_acceptances")
    op.drop_table("legal_acceptances")
