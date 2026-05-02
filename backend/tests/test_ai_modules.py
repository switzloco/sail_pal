"""
Unit tests for AI subsystem modules.

Covers: mode_state, prompt_templates, OllamaRouter model selection,
image_parser JSON extraction, and RAGEngine (mocked ChromaDB).
"""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ── mode_state ───────────────────────────────────────────────────────────────

class TestModeState:
    def test_get_mode_returns_string(self):
        from backend.ai import mode_state
        mode = mode_state.get_mode()
        assert mode in ("cloud", "local")

    def test_set_mode_local(self):
        from backend.ai import mode_state
        original = mode_state.get_mode()
        try:
            mode_state.set_mode("local")
            assert mode_state.get_mode() == "local"
            assert mode_state.is_cloud() is False
        finally:
            mode_state.set_mode(original)

    def test_set_mode_cloud(self):
        from backend.ai import mode_state
        original = mode_state.get_mode()
        try:
            mode_state.set_mode("cloud")
            assert mode_state.get_mode() == "cloud"
            assert mode_state.is_cloud() is True
        finally:
            mode_state.set_mode(original)

    def test_set_mode_invalid(self):
        from backend.ai import mode_state
        with pytest.raises(ValueError, match="Invalid mode"):
            mode_state.set_mode("quantum")


# ── prompt_templates ─────────────────────────────────────────────────────────

class TestPromptTemplates:
    def test_disclaimer_present(self):
        from backend.ai.prompt_templates import DISCLAIMER
        assert "AI-generated" in DISCLAIMER
        assert "rescue services" in DISCLAIMER

    def test_medical_system_mentions_mpic(self):
        from backend.ai.prompt_templates import MEDICAL_SYSTEM
        assert "MPIC" in MEDICAL_SYSTEM

    def test_engine_system_mentions_safety(self):
        from backend.ai.prompt_templates import ENGINE_SYSTEM
        assert "safety" in ENGINE_SYSTEM.lower()

    def test_general_system_mentions_gemma(self):
        from backend.ai.prompt_templates import GENERAL_SYSTEM
        assert "Gemma" in GENERAL_SYSTEM

    def test_mock_chunks_end_with_disclaimer(self):
        from backend.ai.prompt_templates import (
            MOCK_MEDICAL_CHUNKS, MOCK_ENGINE_CHUNKS, DISCLAIMER,
        )
        assert DISCLAIMER in MOCK_MEDICAL_CHUNKS[-1]
        assert DISCLAIMER in MOCK_ENGINE_CHUNKS[-1]


# ── OllamaRouter ────────────────────────────────────────────────────────────

class TestOllamaRouter:
    def test_pick_model_minor(self):
        from backend.ai.ollama_client import OllamaRouter
        router = OllamaRouter(
            host="http://localhost:11434",
            model_primary="gemma4:12b",
            model_scale="gemma4:27b",
        )
        assert router._pick_model("minor") == "gemma4:12b"
        assert router._pick_model("moderate") == "gemma4:12b"

    def test_pick_model_critical(self):
        from backend.ai.ollama_client import OllamaRouter
        router = OllamaRouter(
            host="http://localhost:11434",
            model_primary="gemma4:12b",
            model_scale="gemma4:27b",
        )
        assert router._pick_model("critical") == "gemma4:27b"
        assert router._pick_model("serious") == "gemma4:27b"


# ── Config ───────────────────────────────────────────────────────────────────

class TestConfig:
    def test_cors_origins_from_string(self):
        from backend.config import Settings
        s = Settings(cors_origins="http://a.com, http://b.com")
        assert s.cors_origins == ["http://a.com", "http://b.com"]

    def test_cors_origins_from_list(self):
        from backend.config import Settings
        s = Settings(cors_origins=["http://a.com"])
        assert s.cors_origins == ["http://a.com"]

    def test_default_database_url(self):
        from backend.config import Settings
        s = Settings()
        assert "sqlite" in s.database_url
