"""Set explicit, separately recorded demo counts. Never creates fake member likes."""
import argparse
import sqlite3
from pathlib import Path
from sqlalchemy.engine import make_url
from app.core.config import Settings, BASE_DIR
from app.db.session import Base, make_database
from app.models.entities import Post, PostLikeBaseline, AuditLog, utcnow


def set_counts(settings, assignments):
    if not assignments or any(count < 0 for count in assignments.values()):
        raise ValueError("Counts must be nonnegative")
    engine, factory = make_database(settings.database_url)
    try:
        Base.metadata.create_all(engine)
        with factory.begin() as db:
            posts = {post_id: db.get(Post, post_id) for post_id in assignments}
            if any(post is None for post in posts.values()):
                raise ValueError("Post not found; nothing updated")
            for post_id, count in assignments.items():
                baseline = db.get(PostLikeBaseline, post_id)
                if baseline is None:
                    db.add(PostLikeBaseline(post_id=post_id, count=count))
                else:
                    baseline.count = count
                db.add(AuditLog(actor_name="local-cli", action="set_demo_likes", target=f"post:{post_id}:demo:{count}"))
        return assignments
    finally:
        engine.dispose()


def main():
    parser=argparse.ArgumentParser(description="Set demo like counts, separate from real likes")
    parser.add_argument("--post", action="append", required=True, help="POST_ID:COUNT")
    args=parser.parse_args()
    assignments={}
    for value in args.post:
        try:
            post_id,count=map(int,value.split(":"))
            if post_id<=0 or count<0:raise ValueError()
            assignments[post_id]=count
        except ValueError:raise SystemExit("Use positive POST_ID:nonnegative_COUNT")
    settings=Settings();settings.validate_secret()
    url=make_url(settings.database_url)
    if url.drivername!="sqlite" or not url.database or url.database==":memory:":raise SystemExit("Local SQLite required")
    path=Path(url.database)
    if not path.is_absolute():path=BASE_DIR/path
    if not path.exists():raise SystemExit("Database not found")
    backups=path.parent/"backups";backups.mkdir(parents=True,exist_ok=True)
    backup=backups/("before-likes-"+utcnow().strftime("%Y%m%dT%H%M%S%fZ")+".db")
    with sqlite3.connect(path) as source,sqlite3.connect(backup) as dest:source.backup(dest)
    set_counts(settings, assignments)
    for post_id,count in assignments.items():print(f"Post {post_id}: demo likes = {count:,}")
    print("Backup:",backup)

if __name__=="__main__":main()
