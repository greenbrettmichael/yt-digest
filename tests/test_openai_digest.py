from unittest.mock import MagicMock, patch

import pytest

from app import generate_newsletter_digest


class TestNewsletterGeneration:
    """Tests for the OpenAI integration and newsletter generation logic."""

    def test_missing_api_key(self, monkeypatch):
        """Test that ValueError is raised when OPENAI_API_KEY is missing."""
        # Forcefully remove the key if it exists in the environment
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        fake_data = [{"title": "Test", "video_id": "1", "transcript": "Content"}]

        with pytest.raises(ValueError, match="OPENAI_API_KEY not found"):
            generate_newsletter_digest(fake_data)

    @patch("app.OpenAI")
    def test_generate_newsletter_success(self, mock_openai_class, monkeypatch):
        """
        Happy path: API Key exists, API returns success.
        Verifies the correct model and prompt structure are passed.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")

        # 1. Mock the API Response structure
        # The chain is: Client() -> chat.completions.create() -> response object
        mock_client = mock_openai_class.return_value
        mock_response = MagicMock()
        mock_response.choices[0].message.content = (
            "Key Takeaways:\n\n- **[00:12](https://www.youtube.com/watch?v=vid123&t=12s)** - Point 1"
        )
        mock_client.chat.completions.create.return_value = mock_response

        # 2. Input Data
        fake_data = [{"title": "Python News", "video_id": "vid123", "transcript": "Use type hinting."}]

        # 3. Call the function
        # We allow the default model to be used to test the default parameter
        result = generate_newsletter_digest(fake_data)

        # 4. Assertions
        assert "Key Takeaways:" in result

        # Verify the API was initialized with the key
        mock_openai_class.assert_called_with(api_key="fake-test-key")

        # Verify the call arguments
        call_args = mock_client.chat.completions.create.call_args
        _, kwargs = call_args

        # Check that the default model was used
        assert kwargs["model"] == "gpt-5-mini-2025-08-07"

        # Check that the messages list contains our specific instructions
        messages = kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert "expert tech newsletter editor" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        # Check for specific formatting rules we added
        assert "Do NOT include a title, headline" in messages[1]["content"]
        assert "Provide between 2 and 5 bullet points" in messages[1]["content"]
        # Check that our data was injected
        assert "Video ID: vid123" in messages[1]["content"]
        assert "[Watch on YouTube]" in result or "Key Takeaways" in result

    @patch("app.OpenAI")
    def test_api_failure_raises_runtime_error(self, mock_openai_class, monkeypatch, caplog):
        """
        Error path: API throws an exception.
        Verifies that the function logs the error and raises a RuntimeError.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")

        # 1. Setup the mock to raise an exception
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create.side_effect = Exception("Rate Limit Exceeded")

        fake_data = [{"title": "Test", "video_id": "1", "transcript": "Content"}]

        # 2. Call and Assert
        with pytest.raises(RuntimeError, match="OpenAI API call failed"):
            generate_newsletter_digest(fake_data)

        # 3. Verify logging
        assert "OpenAI API call failed: Rate Limit Exceeded" in caplog.text

    @patch("app.OpenAI")
    def test_custom_model_parameter(self, mock_openai_class, monkeypatch):
        """Test that passing a custom model argument overrides the default."""
        monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")

        mock_client = mock_openai_class.return_value
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Success"
        mock_client.chat.completions.create.return_value = mock_response

        generate_newsletter_digest([], model="gpt-4o-custom")

        # Check that the specific model was passed to the API
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4o-custom"

    @patch("app.OpenAI")
    def test_timestamp_integration(self, mock_openai_class, monkeypatch):
        """Test that transcript data with timestamps is correctly formatted in the prompt."""
        monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")

        mock_client = mock_openai_class.return_value
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Success"
        mock_client.chat.completions.create.return_value = mock_response

        # Test data with new timestamp format
        fake_data = [
            {
                "title": "Test Video",
                "video_id": "abc123",
                "transcript": [
                    {"text": "Hello world", "start": 0},
                    {"text": "This is a test", "start": 10.5},
                    {"text": "End of video", "start": 125.7},
                ],
            }
        ]

        generate_newsletter_digest(fake_data)

        # Verify the prompt includes timestamp instructions
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_prompt = messages[1]["content"]

        # Check for timestamp formatting instructions
        assert "MM:SS" in user_prompt
        assert "timestamp" in user_prompt.lower()
        assert "&t=" in user_prompt

        # Check that transcript data includes timestamps
        assert "[0s] Hello world" in user_prompt
        assert "[10s] This is a test" in user_prompt
        assert "[126s] End of video" in user_prompt  # 125.7 rounds to 126

    @patch("app.OpenAI")
    def test_backward_compatibility_with_string_transcript(self, mock_openai_class, monkeypatch):
        """Test that old format (string transcript) still works as fallback."""
        monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")

        mock_client = mock_openai_class.return_value
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Success"
        mock_client.chat.completions.create.return_value = mock_response

        # Test data with old string format
        fake_data = [{"title": "Test", "video_id": "123", "transcript": "This is plain text"}]

        generate_newsletter_digest(fake_data)

        # Verify it doesn't crash and uses the fallback
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_prompt = messages[1]["content"]

        # Should still contain the transcript text
        assert "This is plain text" in user_prompt
