"""Local post pinning with database backup and audit history."""
import argparse
import sqlite3
from pathlib import Path
from sqlalchemy.engine import make_url
from app.core.config import Settings, BASE_DIR
from app.db.session import Base, make_database
from app.models.entities import Post, PostPin, AuditLog, utcnow


def set_pins(settings, assignments):
    if not assignments or any(value <= 0 for value in assignments.values()):
        raise ValueError("Pin priorities must be positive")
    engine, factory = make_database(settings.database_url)
    try:
        Base.metadata.create_all(engine)
        with factory.begin() as db:
            if any(db.get(Post, post_id) is None for post_id in assignments):
                raise ValueError("Post not found; nothing pinned")
            for post_id, priority in assignments.items():
                pin = db.get(PostPin, post_id)
                if pin is None: db.add(PostPin(post_id=post_id, priority=priority))
                else: pin.priority = priority
                db.add(AuditLog(actor_name="local-cli", action="pin_post", target=f"post:{post_id}:priority:{priority}"))
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Pin existing posts locally")
    parser.add_argument("--post", action="append", required=True, help="POST_ID:PRIORITY")
    args = parser.parse_args()
    try:
        assignments = dict(tuple(map(int, value.split(":"))) for value in args.post)
        if any(key <= 0 or value <= 0 for key,value in assignments.items()): raise ValueError()
    except (ValueError, TypeError): raise SystemExit("Use POST_ID:positive_PRIORITY")
    settings = Settings(); settings.validate_secret()
    url = make_url(settings.database_url)
    if url.drivername != "sqlite" or not url.database or url.database == ":memory:": raise SystemExit("Local SQLite required")
    path = Path(url.database)
    if not path.is_absolute(): path = BASE_DIR/path
    if not path.exists(): raise SystemExit("Database not found")
    backups = path.parent/"backups"; backups.mkdir(parents=True,exist_ok=True)
    backup = backups/("before-pins-"+utcnow().strftime("%Y%m%dT%H%M%S%fZ")+".db")
    with sqlite3.connect(path) as source, sqlite3.connect(backup) as dest: source.backup(dest)
    set_pins(settings, assignments)
    for post_id,priority in assignments.items(): print(f"Pinned post {post_id}: priority {priority}")
    print("Backup:",backup)

if __name__ == "__main__": main()
