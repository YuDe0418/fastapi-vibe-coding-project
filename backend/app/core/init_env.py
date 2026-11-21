from pathlib import Path
import secrets
from .config import BASE_DIR

if __name__ == "__main__":
    target = BASE_DIR / ".env"
    if target.exists():
        print("Existing .env retained")
    else:
        template = (BASE_DIR / ".env.example").read_text(encoding="utf-8")
        with target.open("x", encoding="utf-8") as stream:
            stream.write(template.replace("REPLACE_WITH_RANDOM_SECRET_AT_LEAST_32_CHARACTERS", secrets.token_urlsafe(48)))
        print("Created local .env with random secret (not displayed)")
