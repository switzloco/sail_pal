import os
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    model_config = {"protected_namespaces": ()}

    # Use VESSEL_OPS_DATA_DIR if set (e.g. /tmp/data in Cloud Run), otherwise local default
    vessel_ops_data_dir: str = "./backend/data"
    database_url: str = ""
    
    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str, info) -> str:
        if v: return v
        # Accessing data_dir from defaults if not provided in environment
        data_dir = os.getenv("VESSEL_OPS_DATA_DIR", "./backend/data")
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.abspath(os.path.join(data_dir, "vessel.db"))
        return f"sqlite:///{db_path}"

    @property
    def data_dir(self) -> str:
        d = os.getenv("VESSEL_OPS_DATA_DIR", self.vessel_ops_data_dir)
        os.makedirs(d, exist_ok=True)
        return os.path.abspath(d)

    @property
    def upload_dir(self) -> str:
        u_dir = os.path.join(self.data_dir, "uploads")
        os.makedirs(u_dir, exist_ok=True)
        return u_dir


    ollama_host: str = "http://localhost:11434"
    model_primary: str = "gemma4:e2b"
    model_scale: str = "gemma4:e4b"
    # Unsloth-finetuned Gemma 4 for medical routes. Empty string means "same
    # as model_primary" so the app works out-of-the-box with no .env entry.
    # The installer writes MODEL_MEDICAL=hf.co/nswitzer/gemma4-maritime-medical-GGUF when the
    # Unsloth GGUF pull succeeds.
    model_medical: str = ""
    cors_origins: List[str] = ["*"]

    @field_validator("model_primary", mode="before")
    @classmethod
    def load_primary_model(cls, v):
        # If explicitly set in environment as MODEL_PRIMARY, Pydantic handles it.
        # Otherwise, check OLLAMA_MODEL as a fallback.
        return v or os.getenv("OLLAMA_MODEL") or "gemma4:e2b"

    @field_validator("model_scale", mode="before")
    @classmethod
    def load_scale_model(cls, v):
        return v or os.getenv("OLLAMA_MODEL_SCALE") or "gemma4:e4b"

    @field_validator("model_medical", mode="before")
    @classmethod
    def load_medical_model(cls, v):
        return v or os.getenv("MODEL_MEDICAL") or ""

    @property
    def effective_medical_model(self) -> str:
        """Unsloth fine-tune when installed, vanilla primary otherwise."""
        return self.model_medical or self.model_primary

    # ── Cloud simulation mode ─────────────────────────────────────────────────
    # When True, all LLM calls go to Google AI Studio instead of local Ollama.
    cloud_mode: bool = False
    
    # Turn this on to enable verbose debug logging to backend/data/logs/vessel_debug.log
    debug_mode: bool = True
    google_api_key: str = ""
    cloud_model: str = "gemma-4-26b-a4b-it"

    @field_validator("google_api_key", mode="before")
    @classmethod
    def load_api_key(cls, v):
        if v: return v
        # Try secret mount path (Cloud Run volume mount)
        secret_path = "/secrets/GOOGLE_API_KEY"
        if os.path.exists(secret_path):
            try:
                with open(secret_path, "r") as f:
                    val = f.read().strip()
                    if val:
                        return val
            except Exception:
                pass
        return v

    # ── Fleet Mechanic / Arize observability ──────────────────────────────────
    # The "Fleet Mechanic" is the cloud-side agent that ingests offline medical
    # inference traces into Arize, runs an LLM-as-judge hallucination eval, and
    # drafts prompt patches to push back to the vessel before it leaves the dock.
    #
    # Traces are ALWAYS captured locally (offline, into SQLite). Arize upload and
    # Gemini evaluation only run dockside, when these credentials are present.
    arize_space_id: str = ""
    arize_api_key: str = ""
    arize_project_name: str = "vessel-ops-medical"
    # Model the Fleet Mechanic uses as the LLM judge / patch author (cloud only).
    fleet_mechanic_model: str = "gemini-2.0-flash"

    @field_validator("arize_space_id", "arize_api_key", mode="before")
    @classmethod
    def load_arize_secret(cls, v, info):
        if v:
            return v
        # Cloud Run volume mount fallback, mirroring GOOGLE_API_KEY handling.
        secret_path = f"/secrets/{info.field_name.upper()}"
        if os.path.exists(secret_path):
            try:
                with open(secret_path, "r") as f:
                    val = f.read().strip()
                    if val:
                        return val
            except Exception:
                pass
        return v

    @property
    def arize_enabled(self) -> bool:
        """True when both Arize credentials are present (dockside / cloud)."""
        return bool(self.arize_space_id and self.arize_api_key)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if v == "*": return ["*"]
            return [origin.strip() for origin in v.split(",")]
        return v

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
