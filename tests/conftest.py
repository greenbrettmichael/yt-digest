from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


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
    mock_transcript.language_code = "en"
    mock_transcript.fetch.return_value = [mock_transcript_item]

    mock_list_obj = MagicMock()
    mock_list_obj.find_transcript.return_value = mock_transcript
    mock_list_obj.__iter__.return_value = iter([mock_transcript])

    mock_api.list.return_value = mock_list_obj
    return mock_api
