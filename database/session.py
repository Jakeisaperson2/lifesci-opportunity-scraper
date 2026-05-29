import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base


def _database_url() -> str:
    db_path = os.getenv("DB_PATH", "data/opportunities.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


engine = create_engine(
    _database_url(),
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist. Safe to call on every startup."""
    Base.metadata.create_all(bind=engine)


def migrate_db():
    """Add any columns missing from existing tables. Safe to call repeatedly."""
    from sqlalchemy import text
    new_columns = {
        "faculty_members": ["lab_assets TEXT", "project_ideas TEXT"],
    }
    with engine.connect() as conn:
        for table, col_defs in new_columns.items():
            try:
                existing = [r[1] for r in conn.execute(text(f"PRAGMA table_info({table})"))]
            except Exception:
                continue
            for col_def in col_defs:
                col_name = col_def.split()[0]
                if col_name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_def}"))
        conn.commit()
