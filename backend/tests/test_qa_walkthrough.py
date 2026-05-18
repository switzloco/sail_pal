import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from backend.config import settings

class TestWalkthroughLogic:
    @patch("backend.routers.setup._is_ollama_installed", return_value=False)
    @patch("backend.routers.setup._check_ollama_running", new_callable=AsyncMock, return_value=False)
    @patch("backend.routers.setup._check_model_ready", new_callable=AsyncMock, return_value=False)
    def test_setup_status_ollama_not_installed(self, mock_ready, mock_running, mock_installed, client):
        r = client.get("/api/setup/status")
        assert r.status_code == 200
        data = r.json()
        assert data["ollama_installed"] is False
        assert data["ollama_running"] is False
        assert data["model_ready"] is False

    @patch("backend.routers.setup._is_ollama_installed", return_value=True)
    @patch("backend.routers.setup._check_ollama_running", new_callable=AsyncMock, return_value=True)
    @patch("backend.routers.setup._check_model_ready", new_callable=AsyncMock, return_value=False)
    def test_setup_status_ollama_running_no_model(self, mock_ready, mock_running, mock_installed, client):
        r = client.get("/api/setup/status")
        assert r.status_code == 200
        data = r.json()
        assert data["ollama_installed"] is True
        assert data["ollama_running"] is True
        assert data["model_ready"] is False

    @patch("backend.routers.setup._is_ollama_installed", return_value=False)
    @patch("backend.routers.setup._check_ollama_running", new_callable=AsyncMock, return_value=False)
    @patch("backend.routers.setup._check_model_ready", new_callable=AsyncMock, return_value=False)
    def test_setup_status_cloud_mode_bypasses_ollama_checks(self, mock_ready, mock_running, mock_installed, client):
        # In cloud mode the app uses Gemini, not Ollama, so the status endpoint
        # short-circuits all Ollama checks and reports the app ready.
        client.post("/api/setup/mode", json={"mode": "cloud"})

        r = client.get("/api/setup/status")
        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "cloud"
        assert data["ollama_installed"] is True
        assert data["ollama_running"] is True
        assert data["model_ready"] is True

        client.post("/api/setup/mode", json={"mode": "local"})

    def test_vessel_info_cycle(self, client):
        # Initial get should create default
        r = client.get("/api/setup/vessel-info")
        assert r.status_code == 200
        assert r.json()["name"] == "My Vessel"
        
        # Update it
        r = client.post("/api/setup/vessel-info", json={"name": "Antigravity", "imo_number": "9999999"})
        assert r.status_code == 200
        assert r.json()["name"] == "Antigravity"
        assert r.json()["imo_number"] == "9999999"
        
        # Verify it persisted
        r = client.get("/api/setup/vessel-info")
        assert r.json()["name"] == "Antigravity"

class TestAIResponseQuality:
    @patch("backend.routers.ai._llm_tokens")
    @patch("backend.routers.ai.get_rag_engine")
    def test_medical_query_prompt_construction(self, mock_rag, mock_llm, client, seed_crew):
        # Mock RAG to return nothing
        mock_rag.return_value.query.return_value = []
        
        # Mock LLM to yield a single token
        async def mock_iter(*args, **kwargs):
            yield "Test response"
        mock_llm.side_effect = mock_iter
        
        payload = {
            "crew_id": seed_crew[0].crew_id,
            "symptoms": ["headache", "blurry vision"],
            "severity": "moderate",
            "vitals": {"bp": "140/90", "hr": 95}
        }
        
        # We use a stream, so we need to iterate it
        with client.stream("POST", "/api/ai/medical-query", json=payload) as r:
            assert r.status_code == 200
            # Stream may emit a leading "model" badge event before tokens —
            # consume events until we see at least one token.
            saw_token = False
            for line in r.iter_lines():
                if "token" in line:
                    saw_token = True
                    break
            assert saw_token, "expected at least one token event in stream"
            
        # Verify the prompt construction (internal check of call args)
        call_args = mock_llm.call_args
        system_prompt = call_args[0][0]
        user_prompt = call_args[0][1]
        
        assert "maritime medical assistant" in system_prompt
        assert "Patient: John Smith" in user_prompt
        assert "headache, blurry vision" in user_prompt
        # The vitals dict is stringified
        assert "'bp': '140/90'" in user_prompt
        assert "AI-generated guidance" in system_prompt  # Disclaimer now in system prompt

    @patch("backend.routers.ai._llm_tokens")
    @patch("backend.routers.ai.get_rag_engine")
    def test_medical_query_with_rag(self, mock_rag, mock_llm, client, seed_crew):
        # Mock RAG to return protocols
        mock_rag.return_value.query.return_value = [
            {"text": "Administer aspirin for chest pain.", "metadata": {"source": "IMGS.pdf"}}
        ]
        
        async def mock_iter(*args, **kwargs):
            yield "Response"
        mock_llm.side_effect = mock_iter
        
        payload = {
            "crew_id": seed_crew[0].crew_id,
            "symptoms": ["chest pain"],
            "severity": "critical"
        }
        
        with client.stream("POST", "/api/ai/medical-query", json=payload) as r:
            assert r.status_code == 200
            
        user_prompt = mock_llm.call_args[0][1]
        assert "Relevant Protocol Excerpts:" in user_prompt
        assert "Administer aspirin" in user_prompt
        assert "Source: IMGS.pdf" in user_prompt

    @patch("backend.routers.ai._llm_tokens")
    @patch("backend.routers.ai.get_rag_engine")
    def test_analyze_component_prompt_construction(self, mock_rag, mock_llm, client, seed_component):
        mock_rag.return_value.query.return_value = [
            {"text": "Check fuel filter for clogs.", "metadata": {"source": "Manual.pdf"}}
        ]
        
        async def mock_iter(*args, **kwargs):
            yield "Diagnosis: Clogged filter"
        mock_llm.side_effect = mock_iter
        
        # This endpoint uses Form data
        data = {
            "component_id": seed_component.component_id,
            "issue_description": "Engine stalling under load",
            "severity": "critical"
        }
        
        with client.stream("POST", "/api/ai/analyze-component", data=data) as r:
            assert r.status_code == 200
            
        call_args = mock_llm.call_args
        system_prompt = call_args[0][0]
        user_prompt = call_args[0][1]
        
        assert "maritime engineering assistant" in system_prompt
        assert "Main Engine" in user_prompt
        assert "Engine stalling under load" in user_prompt
        assert "Check fuel filter" in user_prompt  # RAG injection
        assert "AI-generated guidance" in system_prompt  # Disclaimer now in system prompt
