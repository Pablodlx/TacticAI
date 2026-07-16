from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = Field(default="local", alias="APP_ENV")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    storage_backend: str = Field(default="local", alias="STORAGE_BACKEND")
    local_storage_path: str = Field(default="./runtime_data", alias="LOCAL_STORAGE_PATH")
    gcp_project_id: str = Field(default="", alias="GCP_PROJECT_ID")
    gcp_region: str = Field(default="europe-west1", alias="GCP_REGION")
    gcs_input_bucket: str = Field(default="", alias="GCS_INPUT_BUCKET")
    gcs_output_bucket: str = Field(default="", alias="GCS_OUTPUT_BUCKET")

    queue_backend: str = Field(default="sync", alias="QUEUE_BACKEND")
    pubsub_topic: str = Field(default="", alias="PUBSUB_TOPIC")
    pubsub_subscription: str = Field(default="", alias="PUBSUB_SUBSCRIPTION")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    database_url: str = Field(default="sqlite:///./runtime_data/jobs.db", alias="DATABASE_URL")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # Auth
    jwt_secret: str = Field(default="dev-secret-change-me", alias="JWT_SECRET")
    access_token_ttl_min: int = Field(default=15, alias="ACCESS_TOKEN_TTL_MIN")
    refresh_token_ttl_days: int = Field(default=30, alias="REFRESH_TOKEN_TTL_DAYS")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    # Stripe / planes
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_starter: str = Field(default="", alias="STRIPE_PRICE_STARTER")
    stripe_price_pro: str = Field(default="", alias="STRIPE_PRICE_PRO")
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")

    # Heatmaps temporales
    heatmap_window_minutes: int = Field(default=5, alias="HEATMAP_WINDOW_MINUTES")

    model_path: str = Field(default="weights/best.pt", alias="MODEL_PATH")
    conf_threshold: float = Field(default=0.3, alias="CONF_THRESHOLD")
    batch_size_seconds: float = Field(default=3.0, alias="BATCH_SIZE_SECONDS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

