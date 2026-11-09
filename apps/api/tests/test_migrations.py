"""Migrations are checked in offline (--sql) mode: no database, no network."""

import io
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

API_DIR = Path(__file__).resolve().parents[1]


def _config(buffer: io.StringIO) -> Config:
    return Config(str(API_DIR / "alembic.ini"), output_buffer=buffer)


def test_single_head() -> None:
    script = ScriptDirectory.from_config(_config(io.StringIO()))
    assert script.get_heads() == ["0006"]


def test_upgrade_enables_pgvector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@db.example/holdsup?sslmode=require")
    buffer = io.StringIO()
    command.upgrade(_config(buffer), "head", sql=True)
    sql = buffer.getvalue()
    assert "CREATE EXTENSION IF NOT EXISTS vector" in sql
    assert "CREATE TABLE provider_usage" in sql
    assert "CREATE TABLE series_cache" in sql
    assert "CREATE TABLE indicators" in sql
    assert "USING hnsw (embedding vector_cosine_ops)" in sql
    for table in ("checks", "claims", "operations", "reports"):
        assert f"CREATE TABLE {table}" in sql
    assert "REFERENCES checks (id) ON DELETE CASCADE" in sql
    assert "USING hnsw (input_embedding vector_cosine_ops)" in sql


def test_downgrade_drops_pgvector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@db.example/holdsup")
    buffer = io.StringIO()
    command.downgrade(_config(buffer), "0001:base", sql=True)
    assert "DROP EXTENSION IF EXISTS vector" in buffer.getvalue()


def test_downgrade_drops_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@db.example/holdsup")
    buffer = io.StringIO()
    command.downgrade(_config(buffer), "0006:0005", sql=True)
    sql = buffer.getvalue()
    assert "DROP TABLE reports" in sql
    assert "DROP INDEX ix_reports_check_id" in sql
