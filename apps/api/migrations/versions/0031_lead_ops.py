"""Lead operations: extra stages, 1 contact → N leads, activities.

Revision ID: 0031_lead_ops
Revises: 0030_lead_capture
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "0031_lead_ops"
down_revision = "0030_lead_capture"
branch_labels = None
depends_on = None

EXTRA_STAGES = (("Propuesta", "proposal", 3), ("Ganado", "won", 4), ("Perdido", "lost", 5))


def upgrade() -> None:
    op.drop_constraint("uq_leads_client_contact", "leads", type_="unique")
    op.add_column("contacts", sa.Column("company", sa.String(length=180), nullable=False, server_default=""))
    op.add_column("leads", sa.Column("notes", sa.Text(), nullable=False, server_default=""))
    op.add_column("leads", sa.Column("next_action", sa.String(length=240), nullable=False, server_default=""))
    op.add_column("leads", sa.Column("score", sa.Integer(), nullable=True))
    op.add_column("leads", sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_leads_last_activity_at", "leads", ["last_activity_at"])
    op.add_column("lead_capture_settings", sa.Column("last_ingest_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("lead_capture_settings", sa.Column("automation_config", sa.JSON(), nullable=True))

    op.create_table(
        "lead_activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=40), nullable=False, server_default="note"),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_activities_agency_id", "lead_activities", ["agency_id"])
    op.create_index("ix_lead_activities_client_id", "lead_activities", ["client_id"])
    op.create_index("ix_lead_activities_lead_id", "lead_activities", ["lead_id"])

    conn = op.get_bind()
    conn.execute(sa.text("UPDATE leads SET last_activity_at = COALESCE(updated_at, created_at) WHERE last_activity_at IS NULL"))
    op.alter_column("leads", "last_activity_at", nullable=False)
    pipelines = conn.execute(sa.text("SELECT id, agency_id, client_id FROM lead_pipelines")).fetchall()
    for pipeline in pipelines:
        existing = {
            row[0]
            for row in conn.execute(
                sa.text("SELECT slug FROM lead_stages WHERE pipeline_id = :pid"),
                {"pid": pipeline[0]},
            ).fetchall()
        }
        for name, slug, position in EXTRA_STAGES:
            if slug in existing:
                continue
            conn.execute(
                sa.text(
                    """
                    INSERT INTO lead_stages (id, agency_id, client_id, pipeline_id, name, slug, position)
                    VALUES (:id, :agency_id, :client_id, :pipeline_id, :name, :slug, :position)
                    """
                ),
                {
                    "id": uuid4(),
                    "agency_id": pipeline[1],
                    "client_id": pipeline[2],
                    "pipeline_id": pipeline[0],
                    "name": name,
                    "slug": slug,
                    "position": position,
                },
            )


def downgrade() -> None:
    op.drop_index("ix_lead_activities_lead_id", table_name="lead_activities")
    op.drop_index("ix_lead_activities_client_id", table_name="lead_activities")
    op.drop_index("ix_lead_activities_agency_id", table_name="lead_activities")
    op.drop_table("lead_activities")
    op.drop_column("lead_capture_settings", "automation_config")
    op.drop_column("lead_capture_settings", "last_ingest_at")
    op.drop_index("ix_leads_last_activity_at", table_name="leads")
    op.drop_column("leads", "last_activity_at")
    op.drop_column("leads", "score")
    op.drop_column("leads", "next_action")
    op.drop_column("leads", "notes")
    op.drop_column("contacts", "company")
    op.create_unique_constraint("uq_leads_client_contact", "leads", ["client_id", "contact_id"])
