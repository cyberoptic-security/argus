#!/usr/bin/env python3
"""Run Alembic migrations, handling the case where tables already exist
from a pre-Alembic create_all setup (no alembic_version table present)."""
import sys

from alembic import command
from alembic.config import Config

cfg = Config("alembic.ini")

try:
    command.upgrade(cfg, "head")
except Exception as e:
    if "DuplicateTable" in type(e).__name__ or "already exists" in str(e).lower():
        print(
            "Tables already exist without Alembic history — "
            "stamping baseline revision and upgrading...",
            flush=True,
        )
        command.stamp(cfg, "0001")
        command.upgrade(cfg, "head")
    else:
        print(f"Migration failed: {e}", file=sys.stderr)
        sys.exit(1)

print("Migrations up to date.", flush=True)
