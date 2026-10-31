"""Additive v4 migration; no existing table is rebuilt or data deleted."""
from pathlib import Path
from datetime import datetime, timezone
import sqlite3
from sqlalchemy import inspect, text
from backend.database import Base


def migrate(engine) -> None:
    tables = inspect(engine).get_table_names()
    if 'tasks' in tables and ('executions' not in tables or 'diagnostic_runs' not in tables) and engine.url.database not in {None,':memory:'}:
        path = Path(engine.url.database).resolve()
        label = '.pre-v4-' if 'executions' not in tables else '.pre-v4.1-'
        backup = path.with_name(path.stem+label+datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')+'.db')
        with sqlite3.connect(str(path)) as source, sqlite3.connect(str(backup)) as destination:
            source.backup(destination)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)'))
        connection.execute(text('INSERT OR IGNORE INTO schema_migrations VALUES (4, :now)'),{'now':datetime.now(timezone.utc).isoformat()})
        connection.execute(text('INSERT OR IGNORE INTO schema_migrations VALUES (401, :now)'),{'now':datetime.now(timezone.utc).isoformat()})
