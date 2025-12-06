import logging
import pytest
from unittest.mock import MagicMock, patch, mock_open
from types import SimpleNamespace
from youtube_transcript_api import TranscriptsDisabled

from app import get_transcript_api, get_recent_transcripts, save_results_to_json

@pytest.fixture
def mock_search_results():
    """Generates fake scrapetube results."""
    return [
        {
            'videoId': 'vid_1',
            'title': {'runs': [{'text': 'Test Video 1'}]}
        },
        {
            'videoId': 'vid_2',
            'title': {'runs': [{'text': 'Test Video 2'}]}
        }
    ]

@pytest.fixture
def mock_transcript_item():
    """Simulates the object returned inside the list by .fetch()."""
    return SimpleNamespace(text="Hello world", start=0, duration=1)

@pytest.fixture
def mock_api_client(mock_transcript_item):
    """
    Creates a fully mocked YouTubeTranscriptApi object.
    Mocks the chain: api.list() -> transcript_list -> .find_transcript() -> .fetch()
    """
    mock_api = MagicMock()
    
    mock_transcript = MagicMock()
    mock_transcript.language_code = 'en'
    mock_transcript.fetch.return_value = [mock_transcript_item]
    
    mock_list_obj = MagicMock()
    mock_list_obj.find_transcript.return_value = mock_transcript
    mock_list_obj.__iter__.return_value = iter([mock_transcript])
    
    mock_api.list.return_value = mock_list_obj
    return mock_api

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


class TestTranscriptsHappyPath:
    """Tests for the standard successful execution paths."""

    @patch('app.scrapetube.get_search')
    def test_search_and_fetch_english_success(self, mock_scrapetube, mock_api_client, mock_search_results):
        # Setup
        mock_scrapetube.return_value = mock_search_results
        
        # Execute
        results = get_recent_transcripts("test", limit=2, api_client=mock_api_client)
        
        # Verify
        assert len(results) == 2
        assert results[0]['video_id'] == 'vid_1'
        assert results[0]['transcript'] == "Hello world"
        
        # Check that we specifically looked for English
        mock_api_client.list.assert_any_call('vid_1')
        mock_api_client.list.return_value.find_transcript.assert_called_with(['en', 'en-US', 'en-GB'])

    @patch('app.scrapetube.get_search')
    def test_search_fallback_language(self, mock_scrapetube, mock_api_client, mock_search_results):
        # Setup: Return 1 video
        mock_scrapetube.return_value = [mock_search_results[0]]
        
        # Simulate: No English found
        mock_list = mock_api_client.list.return_value
        mock_list.find_transcript.side_effect = Exception("No English")
        
        # Simulate: Fallback (Spanish) found via iterator
        mock_spanish_transcript = MagicMock()
        mock_spanish_transcript.language_code = 'es'
        mock_spanish_transcript.fetch.return_value = [SimpleNamespace(text="Hola mundo")]
        mock_list.__iter__.return_value = iter([mock_spanish_transcript])

        # Execute
        results = get_recent_transcripts("test", limit=1, api_client=mock_api_client)
        
        # Verify
        assert len(results) == 1
        assert results[0]['transcript'] == "Hola mundo"


class TestTranscriptsEdgeCases:
    """Tests for error handling, limits, and malformed data."""

    @patch('app.scrapetube.get_search')
    def test_transcripts_disabled(self, mock_scrapetube, mock_api_client, mock_search_results):
        mock_scrapetube.return_value = mock_search_results
        
        # Simulate: API raises TranscriptsDisabled
        mock_api_client.list.side_effect = TranscriptsDisabled("vid_1")
        
        results = get_recent_transcripts("test", limit=1, api_client=mock_api_client)
        
        # Should return empty list (skipped)
        assert len(results) == 0

    @patch('app.scrapetube.get_search')
    def test_bad_title_structure(self, mock_scrapetube, mock_api_client):
        # Simulate: Video object missing the standard title structure
        bad_video = {'videoId': 'vid_bad', 'title': {}} 
        mock_scrapetube.return_value = [bad_video]
        
        results = get_recent_transcripts("test", limit=1, api_client=mock_api_client)
        
        assert len(results) == 1
        assert results[0]['title'] == "Unknown Title"

    @patch('app.scrapetube.get_search')
    def test_limit_enforcement(self, mock_scrapetube, mock_api_client):
        # Simulate: Search returns 10 videos
        many_videos = [{'videoId': f'v_{i}', 'title': {'runs': [{'text': f'T_{i}'}]}} for i in range(10)]

        mock_scrapetube.side_effect = lambda query, limit, **kwargs: many_videos[:limit]
        
        # Execute: Request limit of 3
        results = get_recent_transcripts("test", limit=3, api_client=mock_api_client)
        
        assert len(results) == 3
        assert results[-1]['video_id'] == 'v_2'

class TestJsonOutput:
    """Tests for the JSON file writing functionality."""

    def test_save_results_to_json_success(self, caplog):
        fake_data = [{'video_id': '123', 'title': 'Test', 'transcript': 'Content'}]
        filename = "test_output.json"
        
        # Ensure we capture INFO logs
        caplog.set_level(logging.INFO)

        with patch("builtins.open", mock_open()) as mocked_file:
            with patch("json.dump") as mocked_dump:
                
                save_results_to_json(fake_data, filename)

                # 1. Verify file operations
                mocked_file.assert_called_once_with(filename, 'w', encoding='utf-8')
                mocked_dump.assert_called_once_with(
                    fake_data, 
                    mocked_file(), 
                    indent=4, 
                    ensure_ascii=False
                )
                
                # 2. Verify Success Log using caplog
                assert f"Successfully saved {len(fake_data)} records to {filename}" in caplog.text

    def test_save_results_io_error(self, caplog):
        """Test that the function logs the error AND re-raises the exception."""
        fake_data = []
        filename = "bad_file.json"
        
        # Ensure we capture ERROR logs
        caplog.set_level(logging.ERROR)
        
        # Simulate a permission denied error
        with patch("builtins.open", mock_open()) as mocked_file:
            mocked_file.side_effect = IOError("Permission denied")
            
            # 1. Verify that the exception is re-raised
            with pytest.raises(IOError):
                save_results_to_json(fake_data, filename)
            
            # 2. Verify the log message was captured by caplog
            # The log message in your function: f"Failed to write to file {filename}: {type(e).__name__}: {e}"
            assert f"Failed to write to file {filename}" in caplog.text
            assert "Permission denied" in caplog.text