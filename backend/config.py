from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    # Use VESSEL_OPS_DATA_DIR if set (e.g. /tmp/data in Cloud Run), otherwise local default
    database_url: str = ""
    
    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str, info) -> str:
        if v: return v
        data_dir = os.getenv("VESSEL_OPS_DATA_DIR", "./backend/data")
        db_path = os.path.join(data_dir, "vessel.db")
        return f"sqlite:///{db_path}"

    ollama_host: str = "http://localhost:11434"
    model_primary: str = "gemma4:e2b"
    model_scale: str = "gemma4:e4b"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # ── Cloud simulation mode ─────────────────────────────────────────────────
    # When True, all LLM calls go to Google AI Studio instead of local Ollama.
    # Useful for testing without the ~8 GB model download.
    # The Ollama setup wizard is bypassed; a cloud-mode banner appears in the UI.
    cloud_mode: bool = False
    google_api_key: str = ""
    cloud_model: str = "gemma-4-26b-a4b-it"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
