from unittest.mock import MagicMock, patch

import pytest
from app import generate_newsletter_digest

class TestNewsletterGeneration:
    """Tests for the OpenAI integration and newsletter generation logic."""

    def test_missing_api_key(self, monkeypatch):
        """Test that ValueError is raised when OPENAI_API_KEY is missing."""
        # Forcefully remove the key if it exists in the environment
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        fake_data = [{'title': 'Test', 'video_id': '1', 'transcript': 'Content'}]
        
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
        mock_response.choices[0].message.content = "### Title: Test\nLink: ...\nKey Takeaways:\n- Point 1"
        mock_client.chat.completions.create.return_value = mock_response
        
        # 2. Input Data
        fake_data = [
            {'title': 'Python News', 'video_id': 'vid123', 'transcript': 'Use type hinting.'}
        ]
        
        # 3. Call the function
        # We allow the default model to be used to test the default parameter
        result = generate_newsletter_digest(fake_data)
        
        # 4. Assertions
        assert "### Title: Test" in result
        
        # Verify the API was initialized with the key
        mock_openai_class.assert_called_with(api_key="fake-test-key")
        
        # Verify the call arguments
        call_args = mock_client.chat.completions.create.call_args
        _, kwargs = call_args
        
        # Check that the default model was used
        assert kwargs['model'] == "gpt-5-mini-2025-08-07"
        
        # Check that the messages list contains our specific instructions
        messages = kwargs['messages']
        assert messages[0]['role'] == "system"
        assert "expert tech newsletter editor" in messages[0]['content']
        assert messages[1]['role'] == "user"
        # Check for specific formatting rules we added
        assert "Do NOT include a main headline" in messages[1]['content']
        assert "Provide between 2 and 5 bullet points" in messages[1]['content']
        # Check that our data was injected
        assert "Video ID: vid123" in messages[1]['content']

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
        
        fake_data = [{'title': 'Test', 'video_id': '1', 'transcript': 'Content'}]
        
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
        assert call_args[1]['model'] == "gpt-4o-custom"