from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agenda"
    api_host: str = "0.0.0.0"
    api_port: int = 8081
    environment: str = "development"
    log_level: str = "INFO"
    log_format: str = "console"
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()