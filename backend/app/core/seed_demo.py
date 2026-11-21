"""Explicit local-only demo data seeding; never executed at application startup."""
import json
import secrets
import sqlite3
from datetime import timedelta
from pathlib import Path
from sqlalchemy import select, or_
from sqlalchemy.engine import make_url
from app.core.config import Settings, BASE_DIR
from app.core.security import hash_password
from app.db.session import Base, make_database
from app.models.entities import User, Post, utcnow
from app.schemas.contracts import Register, PostInput


def seed_demo(settings):
    dataset=json.loads(Path(__file__).with_name("demo_posts.json").read_text(encoding="utf-8"))
    engine,factory=make_database(settings.database_url)
    now=utcnow()
    credentials=[]
    try:
        Base.metadata.create_all(engine)
        with factory.begin() as db:
            names=[item["username"] for item in dataset]
            emails=[name+"@example.com" for name in names]
            if db.scalar(select(User.id).where(or_(User.username.in_(names),User.email.in_(emails))).limit(1)) is not None:
                raise ValueError("Demo username/email already exists. Nothing inserted or overwritten.")
            users=[]
            for item in dataset:
                password="Demo-"+secrets.token_urlsafe(15)
                validated=Register(username=item["username"],nickname=item["nickname"],email=item["username"]+"@example.com",password=password)
                user=User(username=validated.username,nickname=validated.nickname,email=str(validated.email),hashed_password=hash_password(password),is_admin=False,must_change_password=False,created_at=now-timedelta(days=1))
                db.add(user);db.flush();users.append(user)
                credentials.append({"username":user.username,"nickname":user.nickname,"password":password,"posts":len(item["posts"])})
            # Round-robin insertion keeps authors interleaved in the newest-first feed.
            entries=[(users[i],item["posts"][round_index]) for round_index in range(4) for i,item in enumerate(dataset) if round_index<len(item["posts"])]
            for index,(user,item) in enumerate(entries):
                created=now-timedelta(minutes=(len(entries)-1-index)*29)
                value=PostInput(title=item["content"].splitlines()[0][:160],content=item["content"],remarks="測試資料；僅參考 Threads 話題改寫，非原文或真人經歷。來源："+item["source_url"],expires_at=created+timedelta(days=7))
                db.add(Post(author_id=user.id,author_name=user.nickname,created_at=created,**value.model_dump()))
        return credentials
    finally:
        engine.dispose()


def main():
    settings=Settings();settings.validate_secret()
    url=make_url(settings.database_url)
    if url.drivername!="sqlite" or not url.database or url.database==":memory:":
        raise SystemExit("This demo seed command supports only a local SQLite file")
    database=Path(url.database)
    if not database.is_absolute():database=BASE_DIR/database
    if not database.exists():raise SystemExit("Start the website once before seeding")
    timestamp=utcnow().strftime("%Y%m%dT%H%M%S%fZ")
    backup_dir=database.parent/"backups";backup_dir.mkdir(parents=True,exist_ok=True)
    backup=backup_dir/f"before-demo-{timestamp}.db"
    with sqlite3.connect(database) as source,sqlite3.connect(backup) as destination:source.backup(destination)
    output=database.parent/f"demo-accounts-{timestamp}.json"
    # Prepare the credentials file before committing any accounts.
    with output.open("x",encoding="utf-8") as stream:
        try:
            credentials=seed_demo(settings)
        except ValueError as error:
            raise SystemExit(str(error))
        json.dump({"notice":"Local test credentials. Do not commit or share publicly.","accounts":credentials},stream,ensure_ascii=False,indent=2)
        stream.write("\n")
    print("Created 6 ordinary demo accounts and 18 active posts")
    for item in credentials:print(f"{item['username']}: {item['posts']} posts")
    print("CREDENTIALS_FILE="+str(output))
    print("BACKUP_FILE="+str(backup))

if __name__=="__main__":main()
