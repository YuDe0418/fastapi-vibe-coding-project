from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")
    secret_key: str = ""
    database_url: str = "sqlite:///./data/board.db"
    cookie_secure: bool = False
    token_minutes: int = 60
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"
    common_ground_dev_origins: str = ""

    def validate_secret(self):
        if len(self.secret_key) < 32 or self.secret_key.startswith("REPLACE_"):
            raise RuntimeError("請設定 backend/.env 的 SECRET_KEY（至少 32 字元）；可執行 python -m app.core.init_env")
