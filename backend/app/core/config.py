from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "BhaavShare API"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "postgresql://user:password@db/bhaavshare"

    # NLP Settings
    USE_BATCHED_INFERENCE: bool = True

    # Auth
    SECRET_KEY: str = "bhaavshare-dev-secret-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Admin bootstrap
    ADMIN_EMAIL: str = "admin@bhaavshare.com"
    ADMIN_PASSWORD: str = "admin123"

    # OAuth — populated from .env; endpoints return 501 when left blank.
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    OAUTH_REDIRECT_BASE: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
