"""Configuration centralisée — chargée depuis .env (gitignoré)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    APP_NAME: str = "StockPilot AI"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # --- Base de données applicative ---
    DATABASE_URL: str = "postgresql+psycopg2://stockpilot:stockpilot@localhost:5432/stockpilot"

    # --- File de travail asynchrone (Redis + RQ) ---
    REDIS_URL: str = "redis://localhost:6379/0"
    RQ_QUEUE_NAME: str = "stockpilot"

    # --- DeepSeek (narrateur LLM) ---
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 2

    # --- Ingestion SAGE X3 (vues SQL Server) ---
    INGESTION_MODE: str = "auto"  # auto | sagex3 | seed
    X3_ODBC_DRIVER: str = "ODBC Driver 18 for SQL Server"
    X3_SALES_SERVER: str = "192.168.0.128\\Sagex3req"
    X3_SALES_DATABASE: str = ""
    X3_SALES_USER: str = "sa"
    X3_SALES_PASSWORD: str = ""
    X3_SALES_VIEW: str = "V_VENTES"
    X3_STOCK_SERVER: str = "192.168.0.99\\SQLX3V11"
    X3_STOCK_DATABASE: str = ""
    X3_STOCK_USER: str = "sa"
    X3_STOCK_PASSWORD: str = ""
    X3_STOCK_VIEW: str = "V_STOCKS"
    X3_QUERY_TIMEOUT_SECONDS: int = 120

    # --- Prévision ---
    FORECAST_ENGINE: str = "ets"  # ets | prophet
    FORECAST_HORIZON_DAYS: int = 30
    MIN_HISTORY_DAYS: int = 14

    # --- Seuils métier ---
    RUPTURE_COVERAGE_DAYS: int = 15
    RUPTURE_CRITICAL_COVERAGE_DAYS: int = 7
    OVERSTOCK_COVERAGE_DAYS: int = 90
    DORMANT_DAYS: int = 60
    ACCELERATION_PCT: float = 0.40
    SAFETY_STOCK_DAYS: int = 15
    DATA_MAX_AGE_DAYS: int = 3

    # --- Planification ---
    BRIEFING_HOUR: int = 8
    BRIEFING_MINUTE: int = 30

    # --- Limites internes ---
    NARRATOR_MAX_SIGNALS: int = 60
    TOP_PRODUCTS_FORECAST: int = 20

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
