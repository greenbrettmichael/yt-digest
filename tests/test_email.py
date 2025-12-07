import logging
from unittest.mock import patch

import pytest

from app import markdown_to_email_html, send_newsletter_resend


class TestEmailSending:

    @patch("app.resend.Emails.send")
    def test_send_email_success(self, mock_send, monkeypatch, caplog):
        """Test happy path for Resend."""
        caplog.set_level(logging.INFO)
        monkeypatch.setenv("RESEND_API_KEY", "re_fake_key")
        monkeypatch.setenv("RESEND_FROM_EMAIL", "me@test.com")

        # Mock successful response
        mock_send.return_value = {"id": "email_12345"}

        send_newsletter_resend(
            subject="Subject",
            body="Body",
            recipients=["recipient@test.com"]
        )

        # Verify call arguments
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["to"] == ["recipient@test.com"]
        assert call_args["from"] == "me@test.com"
        assert call_args["text"] == "Body"

        # Verify logs
        assert "Email sent successfully" in caplog.text

    def test_missing_credentials(self, monkeypatch, caplog):
        monkeypatch.delenv("RESEND_API_KEY", raising=False)
        send_newsletter_resend("Subj", "Body", ["r@test.com"])
        assert "Skipping email" in caplog.text

    @patch("app.resend.Emails.send")
    def test_resend_failure(self, mock_send, monkeypatch, caplog):
        monkeypatch.setenv("RESEND_API_KEY", "re_fake_key")

        # Simulate Exception
        mock_send.side_effect = Exception("Invalid API Key")

        with pytest.raises(RuntimeError, match="Resend Error"):
            send_newsletter_resend("Subj", "Body", ["r@test.com"])

        assert "Failed to send email" in caplog.text

    @patch("app.resend.Emails.send")
    def test_send_email_generates_html(self, mock_send, monkeypatch, caplog):
        """Test that Markdown is converted and passed to the 'html' parameter."""
        monkeypatch.setenv("RESEND_API_KEY", "re_fake")
        mock_send.return_value = {"id": "123"}

        raw_markdown = "# Hello\n- Item 1"

        send_newsletter_resend(
            subject="Subj",
            body=raw_markdown,
            recipients=["r@test.com"]
        )

        call_args = mock_send.call_args[0][0]

        # 1. Verify Plain Text is passed
        assert call_args["text"] == raw_markdown

        # 2. Verify HTML is generated and passed
        assert "html" in call_args
        assert "<h1>Hello</h1>" in call_args["html"]
        assert "<li>Item 1</li>" in call_args["html"]
        assert "font-family" in call_args["html"] # Checks if CSS was added

    @patch("app.resend.Emails.send")
    def test_resend_response_without_id(self, mock_send, monkeypatch, caplog):
        """Test that an error is raised when Resend returns a response without an 'id' field."""
        caplog.set_level(logging.ERROR)
        monkeypatch.setenv("RESEND_API_KEY", "re_fake_key")
        monkeypatch.setenv("RESEND_FROM_EMAIL", "me@test.com")

        # Mock response without 'id' field
        mock_send.return_value = {"error": "some_error"}

        with pytest.raises(RuntimeError, match="Resend did not return an ID"):
            send_newsletter_resend(
                subject="Subject",
                body="Body",
                recipients=["recipient@test.com"]
            )

        # Verify the error was logged
        assert "Resend did not return an ID" in caplog.text
        assert "some_error" in caplog.text

class TestMarkdownConversion:
    """Tests for the markdown_to_email_html helper function."""

    def test_basic_markdown_conversion(self):
        """Verify standard Markdown elements are converted to HTML tags."""
        md_input = "# Title\n\n- Item 1\n- Item 2"
        html_output = markdown_to_email_html(md_input)

        # Check for Header conversion
        assert "<h1>Title</h1>" in html_output
        # Check for List conversion
        assert "<ul>" in html_output
        assert "<li>Item 1</li>" in html_output
        assert "<li>Item 2</li>" in html_output

    def test_html_wrapper_structure(self):
        """Verify the output contains the necessary email HTML boilerplate."""
        md_input = "Content"
        html_output = markdown_to_email_html(md_input)

        # Check for Doctype and basic structure
        assert "<!DOCTYPE html>" in html_output
        assert "<html>" in html_output
        assert "<body>" in html_output

        # Check for your specific container class
        assert '<div class="container">' in html_output
        # Check for the footer
        assert '<div class="footer">' in html_output

    def test_css_styles_applied(self):
        """Verify that specific CSS rules are embedded in the head."""
        md_input = "Content"
        html_output = markdown_to_email_html(md_input)

        # Check for critical styling elements
        assert "<style>" in html_output
        # Check for font family definition
        assert "font-family: -apple-system" in html_output
        # Check for specific link styling
        assert "a { color: #0066cc;" in html_output.replace("\n", " ")

    def test_link_rendering(self):
        """Verify that links are rendered correctly."""
        md_input = "[Click Me](https://example.com)"
        html_output = markdown_to_email_html(md_input)

        assert '<a href="https://example.com">Click Me</a>' in html_output

    def test_empty_input(self):
        """Verify the function handles empty input without crashing."""
        html_output = markdown_to_email_html("")

        # Should still have the wrapper, just empty content body
        assert '<div class="container">' in html_output
        assert "Generated by AI" in html_output
