from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = ""
    log_level: str = "INFO"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173"]

    # Phase 8: SQLite persistence (opt-in).  Empty string disables persistence
    # entirely; ":memory:" runs an ephemeral DB; a path enables file-backed.
    db_path: str = ""
    # Token TTL in seconds; spec §13-1 / D47: Phase 8+ ⇒ 24h.
    token_ttl_seconds: int = 60 * 60 * 24


settings = Settings()
