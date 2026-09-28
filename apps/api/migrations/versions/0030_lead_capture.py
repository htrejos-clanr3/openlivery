"""Per-client automatic lead capture.

Revision ID: 0030_lead_capture
Revises: 0029_user_automation_runs
"""

from alembic import op
import sqlalchemy as sa


revision = "0030_lead_capture"
down_revision = "0029_user_automation_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_pipelines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_pipelines_agency_id", "lead_pipelines", ["agency_id"])
    op.create_index("ix_lead_pipelines_client_id", "lead_pipelines", ["client_id"])

    op.create_table(
        "lead_stages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=40), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pipeline_id"], ["lead_pipelines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_stages_agency_id", "lead_stages", ["agency_id"])
    op.create_index("ix_lead_stages_client_id", "lead_stages", ["client_id"])
    op.create_index("ix_lead_stages_pipeline_id", "lead_stages", ["pipeline_id"])

    op.create_table(
        "lead_capture_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sources", sa.JSON(), nullable=False, server_default='["whatsapp", "form", "webhook"]'),
        sa.Column("default_pipeline_id", sa.Uuid(), nullable=True),
        sa.Column("default_stage_id", sa.Uuid(), nullable=True),
        sa.Column("default_assignee_user_id", sa.Uuid(), nullable=True),
        sa.Column("auto_tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("notify_on_new_lead", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("ingest_token", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["default_pipeline_id"], ["lead_pipelines.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["default_stage_id"], ["lead_stages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["default_assignee_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id"),
        sa.UniqueConstraint("ingest_token"),
    )
    op.create_index("ix_lead_capture_settings_agency_id", "lead_capture_settings", ["agency_id"])

    op.create_table(
        "contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("channel_identifier", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("extra", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contacts_agency_id", "contacts", ["agency_id"])
    op.create_index("ix_contacts_client_id", "contacts", ["client_id"])
    op.create_index(
        "uq_contacts_client_email",
        "contacts",
        ["client_id", "email"],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL AND email <> ''"),
    )
    op.create_index(
        "uq_contacts_client_phone",
        "contacts",
        ["client_id", "phone"],
        unique=True,
        postgresql_where=sa.text("phone IS NOT NULL AND phone <> ''"),
    )
    op.create_index(
        "uq_contacts_client_channel",
        "contacts",
        ["client_id", "channel_identifier"],
        unique=True,
        postgresql_where=sa.text("channel_identifier IS NOT NULL AND channel_identifier <> ''"),
    )

    op.add_column(
        "conversations",
        sa.Column("contact_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_conversations_contact_id", "conversations", ["contact_id"])
    op.create_foreign_key(
        "fk_conversations_contact_id",
        "conversations",
        "contacts",
        ["contact_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("pipeline_id", sa.Uuid(), nullable=True),
        sa.Column("stage_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_user_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pipeline_id"], ["lead_pipelines.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["stage_id"], ["lead_stages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "contact_id", name="uq_leads_client_contact"),
    )
    op.create_index("ix_leads_agency_id", "leads", ["agency_id"])
    op.create_index("ix_leads_client_id", "leads", ["client_id"])
    op.create_index("ix_leads_contact_id", "leads", ["contact_id"])
    op.create_index("ix_leads_conversation_id", "leads", ["conversation_id"])
    op.create_index("ix_leads_assigned_user_id", "leads", ["assigned_user_id"])

    op.create_table(
        "lead_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False, server_default="new_lead"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_notifications_agency_id", "lead_notifications", ["agency_id"])
    op.create_index("ix_lead_notifications_client_id", "lead_notifications", ["client_id"])
    op.create_index("ix_lead_notifications_user_id", "lead_notifications", ["user_id"])
    op.create_index("ix_lead_notifications_lead_id", "lead_notifications", ["lead_id"])

    op.create_table(
        "lead_capture_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="success"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_capture_events_agency_id", "lead_capture_events", ["agency_id"])
    op.create_index("ix_lead_capture_events_client_id", "lead_capture_events", ["client_id"])
    op.create_index("ix_lead_capture_events_status", "lead_capture_events", ["status"])


def downgrade() -> None:
    op.drop_index("ix_lead_capture_events_status", table_name="lead_capture_events")
    op.drop_index("ix_lead_capture_events_client_id", table_name="lead_capture_events")
    op.drop_index("ix_lead_capture_events_agency_id", table_name="lead_capture_events")
    op.drop_table("lead_capture_events")
    op.drop_index("ix_lead_notifications_lead_id", table_name="lead_notifications")
    op.drop_index("ix_lead_notifications_user_id", table_name="lead_notifications")
    op.drop_index("ix_lead_notifications_client_id", table_name="lead_notifications")
    op.drop_index("ix_lead_notifications_agency_id", table_name="lead_notifications")
    op.drop_table("lead_notifications")
    op.drop_index("ix_leads_assigned_user_id", table_name="leads")
    op.drop_index("ix_leads_conversation_id", table_name="leads")
    op.drop_index("ix_leads_contact_id", table_name="leads")
    op.drop_index("ix_leads_client_id", table_name="leads")
    op.drop_index("ix_leads_agency_id", table_name="leads")
    op.drop_table("leads")
    op.drop_constraint("fk_conversations_contact_id", "conversations", type_="foreignkey")
    op.drop_index("ix_conversations_contact_id", table_name="conversations")
    op.drop_column("conversations", "contact_id")
    op.drop_index("uq_contacts_client_channel", table_name="contacts")
    op.drop_index("uq_contacts_client_phone", table_name="contacts")
    op.drop_index("uq_contacts_client_email", table_name="contacts")
    op.drop_index("ix_contacts_client_id", table_name="contacts")
    op.drop_index("ix_contacts_agency_id", table_name="contacts")
    op.drop_table("contacts")
    op.drop_index("ix_lead_capture_settings_agency_id", table_name="lead_capture_settings")
    op.drop_table("lead_capture_settings")
    op.drop_index("ix_lead_stages_pipeline_id", table_name="lead_stages")
    op.drop_index("ix_lead_stages_client_id", table_name="lead_stages")
    op.drop_index("ix_lead_stages_agency_id", table_name="lead_stages")
    op.drop_table("lead_stages")
    op.drop_index("ix_lead_pipelines_client_id", table_name="lead_pipelines")
    op.drop_index("ix_lead_pipelines_agency_id", table_name="lead_pipelines")
    op.drop_table("lead_pipelines")
