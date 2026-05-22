"""Add dns_checks and dns_check_results tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-30
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dns_checks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fqdns", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_dns_checks_scan_id", "dns_checks", ["scan_id"])

    op.create_table(
        "dns_check_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("check_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fqdn", sa.Text(), nullable=False),
        sa.Column("check_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["check_id"], ["dns_checks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_dns_check_results_check_id", "dns_check_results", ["check_id"])
    op.create_index("idx_dns_check_results_fqdn", "dns_check_results", ["fqdn"])


def downgrade() -> None:
    op.drop_index("idx_dns_check_results_fqdn", table_name="dns_check_results")
    op.drop_index("idx_dns_check_results_check_id", table_name="dns_check_results")
    op.drop_table("dns_check_results")
    op.drop_index("idx_dns_checks_scan_id", table_name="dns_checks")
    op.drop_table("dns_checks")
