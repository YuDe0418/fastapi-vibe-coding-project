from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import BASE_DIR

class Base(DeclarativeBase):
    pass

def make_database(url):
    parsed = make_url(url)
    if parsed.drivername.startswith("sqlite") and parsed.database and parsed.database != ":memory:":
        path = Path(parsed.database)
        if not path.is_absolute():
            path = BASE_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)
        url = parsed.set(database=str(path))
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 15} if parsed.drivername.startswith("sqlite") else {})
    if parsed.drivername.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
    return engine, sessionmaker(bind=engine, expire_on_commit=False)
