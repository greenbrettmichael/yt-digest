from unittest.mock import patch
import pytest

from app import get_transcript_api


class TestConfiguration:
    """Tests related to environment setup and API initialization."""

    def test_get_transcript_api_missing_credentials(self, monkeypatch):
        monkeypatch.setenv("PROXY_USERNAME", "")
        monkeypatch.setenv("PROXY_PASSWORD", "")
        
        with pytest.raises(ValueError, match="Proxy credentials not found"):
            get_transcript_api()

    @patch('app.YouTubeTranscriptApi')
    @patch('app.WebshareProxyConfig')
    def test_get_transcript_api_success(self, mock_proxy_config, mock_api_class, monkeypatch):
        monkeypatch.setenv("PROXY_USERNAME", "myuser")
        monkeypatch.setenv("PROXY_PASSWORD", "mypass")
        
        api = get_transcript_api()
        
        mock_proxy_config.assert_called_with(proxy_username="myuser", proxy_password="mypass")
        mock_api_class.assert_called_once()
        assert api == mock_api_class.return_value