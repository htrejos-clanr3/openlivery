"""Scheduling: availability, appointments and their audit trail.

Revision ID: 0042_agenda
Revises: 0041_ucp
"""

from alembic import op
import sqlalchemy as sa

revision = "0042_agenda"
down_revision = "0041_ucp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/Bogota"),
    )

    op.create_table(
        "availability_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_time", sa.Time(), nullable=False, server_default="09:00"),
        sa.Column("end_time", sa.Time(), nullable=False, server_default="18:00"),
        sa.Column("slot_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("buffer_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_availability_rules_agency_id", "availability_rules", ["agency_id"])
    op.create_index("ix_availability_rules_client_id", "availability_rules", ["client_id"])

    op.create_table(
        "availability_exceptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exception_date", sa.Date(), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("note", sa.String(240), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_availability_exceptions_agency_id", "availability_exceptions", ["agency_id"])
    op.create_index("ix_availability_exceptions_client_id", "availability_exceptions", ["client_id"])
    op.create_index("ix_availability_exceptions_exception_date", "availability_exceptions", ["exception_date"])

    op.create_table(
        "appointments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.Uuid(), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lead_id", sa.Uuid(), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="scheduled"),
        sa.Column("source", sa.String(32), nullable=False, server_default="panel"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("external_event_id", sa.String(160), nullable=True),
        sa.Column("meeting_url", sa.String(400), nullable=True),
        sa.Column("cancelled_reason", sa.String(240), nullable=True),
        sa.Column("idempotency_key", sa.String(80), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_appointments_agency_id", "appointments", ["agency_id"])
    op.create_index("ix_appointments_client_id", "appointments", ["client_id"])
    op.create_index("ix_appointments_starts_at", "appointments", ["starts_at"])
    op.create_index("ix_appointments_ends_at", "appointments", ["ends_at"])
    op.create_index("ix_appointments_status", "appointments", ["status"])

    op.create_table(
        "appointment_audits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("appointment_id", sa.Uuid(), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(32), nullable=False, server_default="created"),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_appointment_audits_appointment_id", "appointment_audits", ["appointment_id"])


def downgrade() -> None:
    op.drop_table("appointment_audits")
    op.drop_table("appointments")
    op.drop_table("availability_exceptions")
    op.drop_table("availability_rules")
    op.drop_column("clients", "timezone")
