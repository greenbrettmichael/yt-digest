from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from youtube_transcript_api import TranscriptsDisabled

from app import get_recent_transcripts


@pytest.fixture
def mock_search_results():
    """Generates fake scrapetube results."""
    return [
        {"videoId": "vid_1", "title": {"runs": [{"text": "Test Video 1"}]}},
        {"videoId": "vid_2", "title": {"runs": [{"text": "Test Video 2"}]}},
    ]


class TestTranscriptsHappyPath:
    """Tests for the standard successful execution paths."""

    @patch("app.scrapetube.get_search")
    def test_search_and_fetch_english_success(self, mock_scrapetube, mock_api_client, mock_search_results):
        # Setup
        mock_scrapetube.return_value = mock_search_results

        # Execute
        results = get_recent_transcripts("test", limit=2, api_client=mock_api_client)

        # Verify
        assert len(results) == 2
        assert results[0]["video_id"] == "vid_1"
        assert results[0]["transcript"] == "Hello world"

        # Check that we specifically looked for English
        mock_api_client.list.assert_any_call("vid_1")
        mock_api_client.list.return_value.find_transcript.assert_called_with(["en", "en-US", "en-GB"])

    @patch("app.scrapetube.get_search")
    def test_search_fallback_language(self, mock_scrapetube, mock_api_client, mock_search_results):
        # Setup: Return 1 video
        mock_scrapetube.return_value = [mock_search_results[0]]

        # Simulate: No English found
        mock_list = mock_api_client.list.return_value
        mock_list.find_transcript.side_effect = Exception("No English")

        # Simulate: Fallback (Spanish) found via iterator
        mock_spanish_transcript = MagicMock()
        mock_spanish_transcript.language_code = "es"
        mock_spanish_transcript.fetch.return_value = [SimpleNamespace(text="Hola mundo")]
        mock_list.__iter__.return_value = iter([mock_spanish_transcript])

        # Execute
        results = get_recent_transcripts("test", limit=1, api_client=mock_api_client)

        # Verify
        assert len(results) == 1
        assert results[0]["transcript"] == "Hola mundo"


class TestTranscriptsEdgeCases:
    """Tests for error handling, limits, and malformed data."""

    @patch("app.scrapetube.get_search")
    def test_transcripts_disabled(self, mock_scrapetube, mock_api_client, mock_search_results):
        mock_scrapetube.return_value = mock_search_results

        # Simulate: API raises TranscriptsDisabled
        mock_api_client.list.side_effect = TranscriptsDisabled("vid_1")

        results = get_recent_transcripts("test", limit=1, api_client=mock_api_client)

        # Should return empty list (skipped)
        assert len(results) == 0

    @patch("app.scrapetube.get_search")
    def test_bad_title_structure(self, mock_scrapetube, mock_api_client):
        # Simulate: Video object missing the standard title structure
        bad_video = {"videoId": "vid_bad", "title": {}}
        mock_scrapetube.return_value = [bad_video]

        results = get_recent_transcripts("test", limit=1, api_client=mock_api_client)

        assert len(results) == 1
        assert results[0]["title"] == "Unknown Title"

    @patch("app.scrapetube.get_search")
    def test_limit_enforcement(self, mock_scrapetube, mock_api_client):
        # Simulate: Search returns 10 videos
        many_videos = [{"videoId": f"v_{i}", "title": {"runs": [{"text": f"T_{i}"}]}} for i in range(10)]

        mock_scrapetube.side_effect = lambda query, limit, **kwargs: many_videos[:limit]

        # Execute: Request limit of 3
        results = get_recent_transcripts("test", limit=3, api_client=mock_api_client)

        assert len(results) == 3
        assert results[-1]["video_id"] == "v_2"


class TestYoutubeUrlSupport:
    """Tests for YouTube URL support in get_recent_transcripts."""

    @patch("app.scrapetube.scrapetube.get_videos")
    def test_get_transcripts_with_url(self, mock_get_videos, mock_api_client, mock_search_results):
        """Test that get_recent_transcripts works with a YouTube search URL."""
        mock_get_videos.return_value = mock_search_results

        # Use a full YouTube URL instead of a keyword
        url = "https://www.youtube.com/results?search_query=news"
        results = get_recent_transcripts(url, limit=2, api_client=mock_api_client)

        # Verify that get_videos was called with the URL
        mock_get_videos.assert_called_once()
        call_args = mock_get_videos.call_args
        assert call_args[1]["url"] == url
        assert call_args[1]["api_endpoint"] == "https://www.youtube.com/youtubei/v1/search"

        # Verify results
        assert len(results) == 2
        assert results[0]["video_id"] == "vid_1"

    @patch("app.scrapetube.scrapetube.get_videos")
    def test_get_transcripts_with_url_and_sp(self, mock_get_videos, mock_api_client, mock_search_results):
        """Test that get_recent_transcripts passes URL with sp parameter directly."""
        mock_get_videos.return_value = mock_search_results

        # Use a URL with both search_query and sp parameters
        url = "https://www.youtube.com/results?search_query=news&sp=CAASBAgCEAE%3D"
        results = get_recent_transcripts(url, limit=2, api_client=mock_api_client)

        # Verify that get_videos was called with the full URL (preserving sp parameter)
        mock_get_videos.assert_called_once()
        call_args = mock_get_videos.call_args
        assert call_args[1]["url"] == url

        # Verify results
        assert len(results) == 2

    @patch("app.scrapetube.get_search")
    def test_backward_compatibility_with_plain_keyword(self, mock_scrapetube, mock_api_client, mock_search_results):
        """Test that plain keywords still work (backward compatibility)."""
        mock_scrapetube.return_value = mock_search_results

        # Use a plain keyword as before
        results = get_recent_transcripts("test keyword", limit=2, api_client=mock_api_client)

        # Verify that scrapetube.get_search was called with the keyword
        mock_scrapetube.assert_called_once()
        call_args = mock_scrapetube.call_args
        assert call_args[1]["query"] == "test keyword"
        assert call_args[1]["sort_by"] == "relevance"

        # Verify results
        assert len(results) == 2
