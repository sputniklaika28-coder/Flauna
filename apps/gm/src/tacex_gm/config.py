from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    log_level: str = "INFO"
    # Backpressure: disconnect client if send queue exceeds this
    ws_max_queue_size: int = 100
    # Phase 0: in-memory only; Phase 8 adds SQLite
    max_rooms: int = 20


settings = Settings()
