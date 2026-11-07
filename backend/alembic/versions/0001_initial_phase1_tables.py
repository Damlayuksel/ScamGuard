"""initial phase1 tables

Revision ID: 0001
Revises:
Create Date: 2026-10-14

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BLACKLIST_SOURCES = ("usom", "urlhaus", "community")
SCAN_LEVELS = ("dangerous", "suspicious", "no_known_threat")


def _enum(values: tuple[str, ...], name: str) -> sa.Enum:
    # The CHECK constraint is declared explicitly below, so the type does not create one.
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=False, length=32)


def _in_check(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def upgrade() -> None:
    op.create_table(
        "blacklist_domains",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("domain", sa.String(length=253), nullable=False),
        sa.Column("source", _enum(BLACKLIST_SOURCES, "blacklist_source"), nullable=False),
        sa.Column(
            "added_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "last_seen", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            _in_check("source", BLACKLIST_SOURCES),
            name=op.f("ck_blacklist_domains_blacklist_source"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blacklist_domains")),
        sa.UniqueConstraint("domain", "source", name=op.f("uq_blacklist_domains_domain_source")),
    )
    op.create_index(op.f("ix_blacklist_domains_domain"), "blacklist_domains", ["domain"])

    op.create_table(
        "domain_reports",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("domain", sa.String(length=253), nullable=False),
        sa.Column("device_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_domain_reports")),
        sa.UniqueConstraint(
            "domain", "device_hash", name=op.f("uq_domain_reports_domain_device_hash")
        ),
    )
    op.create_index(op.f("ix_domain_reports_domain"), "domain_reports", ["domain"])

    op.create_table(
        "scan_stats",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("domain", sa.String(length=253), nullable=True),
        sa.Column("level", _enum(SCAN_LEVELS, "scan_level"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(_in_check("level", SCAN_LEVELS), name=op.f("ck_scan_stats_scan_level")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scan_stats")),
    )


def downgrade() -> None:
    op.drop_table("scan_stats")
    op.drop_index(op.f("ix_domain_reports_domain"), table_name="domain_reports")
    op.drop_table("domain_reports")
    op.drop_index(op.f("ix_blacklist_domains_domain"), table_name="blacklist_domains")
    op.drop_table("blacklist_domains")
