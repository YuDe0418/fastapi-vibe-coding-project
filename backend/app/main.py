from contextlib import asynccontextmanager
from threading import Lock
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from app.core.config import Settings
from app.db.session import Base, make_database
from app.api.routers import users, posts, admin


def create_app(settings: Settings | None=None):
    config=settings or Settings()
    allowed_origins = set(config.allowed_origins.split(","))
    if config.common_ground_dev_origins:
        allowed_origins.update(config.common_ground_dev_origins.split(","))
    @asynccontextmanager
    async def lifespan(app):
        config.validate_secret()
        engine,factory=make_database(config.database_url)
        Base.metadata.create_all(engine)
        app.state.engine=engine;app.state.session_factory=factory
        yield
        engine.dispose()
    app=FastAPI(title="Common Ground · 交流廣場",version="1.0.0",lifespan=lifespan)
    app.state.settings=config;app.state.login_attempts={};app.state.login_lock=Lock()

    @app.middleware("http")
    async def security(request:Request,call_next):
        origin=request.headers.get("origin")
        if request.method not in {"GET","HEAD","OPTIONS"}:
            if origin and origin not in allowed_origins:
                return JSONResponse({"detail":"不允許的請求來源"},status_code=403)
            if request.headers.get("sec-fetch-site")=="cross-site":
                return JSONResponse({"detail":"不允許跨站操作"},status_code=403)
        response=await call_next(request)
        response.headers["X-Content-Type-Options"]="nosniff"
        response.headers["X-Frame-Options"]="DENY"
        response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
        if request.url.path.startswith(("/users","/api/users","/api/admin","/posts","/api/posts")):
            response.headers["Cache-Control"]="no-store"
        return response

    app.include_router(users.router);app.include_router(posts.router)
    app.include_router(users.router,prefix="/api");app.include_router(posts.router,prefix="/api")
    app.include_router(admin.router,prefix="/api")

    @app.get("/health")
    @app.get("/api/health")
    def health():
        with app.state.session_factory() as db:db.execute(select(1))
        return {"status":"ok","version":"1.0.0"}
    return app

app=create_app()
