from __future__ import annotations

import os

from pydantic import BaseModel


class Config(BaseModel):
    jwt_secret: str = os.environ.get("JWT_SECRET", "dev-secret-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    host: str = os.environ.get("HOST", "0.0.0.0")
    port: int = int(os.environ.get("PORT", "8000"))
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    use_mock_llm: bool = os.environ.get("USE_MOCK_LLM", "true").lower() == "true"


config = Config()
