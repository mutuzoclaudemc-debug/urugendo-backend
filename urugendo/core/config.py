from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/urugendo_db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_postgres_url(cls, v: str) -> str:
        # Render provides postgres:// but SQLAlchemy 2.0 requires postgresql://
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # MTN MoMo
    MTN_MOMO_BASE_URL: str = "https://sandbox.momodeveloper.mtn.com"
    MTN_MOMO_SUBSCRIPTION_KEY: str = ""
    MTN_MOMO_API_USER: str = ""
    MTN_MOMO_API_KEY: str = ""
    MTN_MOMO_ENVIRONMENT: str = "sandbox"
    MTN_MOMO_CURRENCY: str = "RWF"
    MTN_MOMO_CALLBACK_URL: str = "https://yourdomain.com/api/payments/mtn/callback"

    # Airtel Money
    AIRTEL_BASE_URL: str = "https://openapi.airtel.africa"
    AIRTEL_CLIENT_ID: str = ""
    AIRTEL_CLIENT_SECRET: str = ""
    AIRTEL_ENVIRONMENT: str = "sandbox"

    APP_NAME: str = "Urugendo"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
