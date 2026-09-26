from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agenda"
    api_host: str = "0.0.0.0"
    api_port: int = 8081
    environment: str = "development"
    log_level: str = "DEBUG"
    log_format: str = "console"
    sql_echo: bool = False
    keycloak_base_url: str = "http://localhost:8080"
    keycloak_realm: str = "agenda"
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    osrm_base_url: str = "https://router.project-osrm.org"
    notificacao_webhook_url: str | None = None
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "agenda@localhost"
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = False
    notificacao_max_tentativas: int = 3
    public_rate_limit_per_minute: int = 60
    database_url: str = (
        "postgresql+psycopg://agenda:agenda@localhost:5432/agenda"
    )
    media_storage_provider: str = "filesystem"
    media_storage_path: str = "./data/media"
    media_base_url: str = "http://localhost:8081"
    opensearch_url: str = "https://localhost:9200"
    opensearch_username: str = "admin"
    # Reaproveita a senha do container local quando OPENSEARCH_PASSWORD nao for definida.
    opensearch_password: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENSEARCH_PASSWORD", "OPENSEARCH_INITIAL_ADMIN_PASSWORD"),
    )
    opensearch_verify_certs: bool = False
    search_worker_name: str | None = None
    search_worker_batch_size: int = 100
    search_worker_max_attempts: int = 5
    search_worker_retry_delay_seconds: int = 60
    search_worker_retry_max_delay_seconds: int = 3600
    search_worker_poll_interval_seconds: float = 1.0
    search_worker_lock_timeout_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()