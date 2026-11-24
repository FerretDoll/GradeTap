"""Explicit CLI entry point for applications previously initialized with this module."""
from pathlib import Path

from alembic import command
from alembic.config import Config


def init_db() -> None:
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    command.upgrade(config, "head")


if __name__ == "__main__":
    init_db()
