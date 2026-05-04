import os
import unittest
from unittest.mock import patch, MagicMock
from backend.web_entrypoint import main, _ensure_data_dir, _run_migrations

class TestWebEntrypoint(unittest.TestCase):
    @patch("backend.web_entrypoint.Path")
    @patch("backend.web_entrypoint.os")
    def test_ensure_data_dir(self, mock_os, mock_path):
        # Test that it creates the directory specified in env
        mock_os.environ.get.return_value = "/tmp/vessel_data"
        mock_dir = MagicMock()
        mock_path.return_value = mock_dir
        
        _ensure_data_dir()
        
        mock_path.assert_called_with("/tmp/vessel_data")
        # Should call mkdir for parents and the uploads subdir
        assert mock_dir.mkdir.called

    @patch("backend.web_entrypoint.subprocess.run")
    def test_run_migrations_success(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Success"
        _run_migrations()
        mock_run.assert_called_once()

    @patch("backend.web_entrypoint.subprocess.run")
    def test_run_migrations_failure(self, mock_run):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Error"
        with self.assertRaises(RuntimeError):
            _run_migrations()

    @patch("uvicorn.run")
    @patch("backend.web_entrypoint._run_migrations")
    @patch("backend.web_entrypoint._auto_seed")
    @patch("backend.web_entrypoint._ensure_data_dir")
    def test_main_smoke(self, mock_ensure, mock_seed, mock_migrations, mock_uvicorn):
        # Mocking ensures we don't actually run migrations or start uvicorn
        mock_ensure.return_value = MagicMock()
        
        with patch.dict("os.environ", {"PORT": "9999"}):
            main()
            
            mock_ensure.assert_called_once()
            mock_migrations.assert_called_once()
            mock_seed.assert_called_once()
            mock_uvicorn.assert_called_once()
            
            _, kwargs = mock_uvicorn.call_args
            assert kwargs["port"] == 9999
            assert kwargs["host"] == "0.0.0.0"
