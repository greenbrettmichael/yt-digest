import json
import logging

import pytest

from app import load_email_list_config


class TestEmailListConfig:
    """Tests for loading and validating email_list.json configuration."""

    def test_load_valid_config(self, tmp_path):
        """Test loading a valid configuration file."""
        config_file = tmp_path / "email_list.json"
        config_data = [
            {"email": "user1@example.com", "search_url": "https://www.youtube.com/results?search_query=python"},
            {"email": "user2@example.com", "search_url": "https://www.youtube.com/results?search_query=ai"},
        ]
        config_file.write_text(json.dumps(config_data))

        result = load_email_list_config(str(config_file))

        assert len(result) == 2
        assert result[0]["email"] == "user1@example.com"
        assert result[0]["search_url"] == "https://www.youtube.com/results?search_query=python"
        assert result[1]["email"] == "user2@example.com"
        assert result[1]["search_url"] == "https://www.youtube.com/results?search_query=ai"

    def test_load_config_strips_whitespace(self, tmp_path):
        """Test that email and URL fields are stripped of whitespace."""
        config_file = tmp_path / "email_list.json"
        config_data = [{"email": "  user@example.com  ", "search_url": "  https://youtube.com/search  "}]
        config_file.write_text(json.dumps(config_data))

        result = load_email_list_config(str(config_file))

        assert result[0]["email"] == "user@example.com"
        assert result[0]["search_url"] == "https://youtube.com/search"

    def test_load_config_file_not_found(self):
        """Test error handling when configuration file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_email_list_config("nonexistent_file.json")

    def test_load_config_invalid_json(self, tmp_path):
        """Test error handling for malformed JSON."""
        config_file = tmp_path / "email_list.json"
        config_file.write_text("{invalid json content")

        with pytest.raises(ValueError, match="Invalid JSON in configuration file"):
            load_email_list_config(str(config_file))

    def test_load_config_not_array(self, tmp_path):
        """Test error handling when JSON is not an array."""
        config_file = tmp_path / "email_list.json"
        config_file.write_text('{"email": "test@example.com"}')

        with pytest.raises(ValueError, match="Configuration must be a JSON array"):
            load_email_list_config(str(config_file))

    def test_load_config_entry_not_object(self, tmp_path):
        """Test error handling when an entry is not an object."""
        config_file = tmp_path / "email_list.json"
        config_file.write_text('["string_entry"]')

        with pytest.raises(ValueError, match="Entry at index 0 must be an object"):
            load_email_list_config(str(config_file))

    def test_load_config_missing_email_field(self, tmp_path, caplog):
        """Test error handling when email field is missing."""
        config_file = tmp_path / "email_list.json"
        config_data = [{"search_url": "https://www.youtube.com/results?search_query=python"}]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.WARNING)
        validated = load_email_list_config(str(config_file))
        assert len(validated) == 0
        assert "Entry at index 0 missing or invalid 'email' field" in caplog.text

    def test_load_config_empty_email_field(self, tmp_path, caplog):
        """Test error handling when email field is empty."""
        config_file = tmp_path / "email_list.json"
        config_data = [{"email": "", "search_url": "https://www.youtube.com/results?search_query=python"}]
        config_file.write_text(json.dumps(config_data))
        caplog.set_level(logging.WARNING)
        validated = load_email_list_config(str(config_file))
        assert len(validated) == 0
        assert "Entry at index 0 missing or invalid 'email' field" in caplog.text

    def test_load_config_whitespace_only_email(self, tmp_path, caplog):
        """Test error handling when email field contains only whitespace."""
        config_file = tmp_path / "email_list.json"
        config_data = [{"email": "   ", "search_url": "https://www.youtube.com/results?search_query=python"}]
        config_file.write_text(json.dumps(config_data))
        caplog.set_level(logging.WARNING)
        validated = load_email_list_config(str(config_file))
        assert len(validated) == 0
        assert "Entry at index 0 missing or invalid 'email' field" in caplog.text

    def test_load_config_missing_search_url_field(self, tmp_path, caplog):
        """Test error handling when search_url field is missing."""
        config_file = tmp_path / "email_list.json"
        config_data = [{"email": "user@example.com"}]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.WARNING)
        validated = load_email_list_config(str(config_file))
        assert len(validated) == 0
        assert "Entry at index 0 missing or invalid 'search_url' field" in caplog.text

    def test_load_config_empty_search_url_field(self, tmp_path, caplog):
        """Test error handling when search_url field is empty."""
        config_file = tmp_path / "email_list.json"
        config_data = [{"email": "user@example.com", "search_url": ""}]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.WARNING)
        validated = load_email_list_config(str(config_file))
        assert len(validated) == 0
        assert "Entry at index 0 missing or invalid 'search_url' field" in caplog.text

    def test_load_config_invalid_email_format(self, tmp_path, caplog):
        """Test error handling for invalid email format (no @ symbol)."""
        config_file = tmp_path / "email_list.json"
        config_data = [
            {"email": "invalid_email_without_at", "search_url": "https://www.youtube.com/results?search_query=python"}
        ]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.WARNING)
        validated = load_email_list_config(str(config_file))
        assert len(validated) == 0
        assert "Entry at index 0 has invalid email format" in caplog.text

    def test_load_config_empty_array(self, tmp_path, caplog):
        """Test error handling when configuration array is empty."""
        config_file = tmp_path / "email_list.json"
        config_file.write_text("[]")

        caplog.set_level(logging.WARNING)
        validated = load_email_list_config(str(config_file))
        assert len(validated) == 0
        assert "Configuration file contains no valid entries" in caplog.text

    def test_load_config_logs_success(self, tmp_path, caplog):
        """Test that successful loading logs appropriate message."""
        config_file = tmp_path / "email_list.json"
        config_data = [{"email": "user@example.com", "search_url": "https://youtube.com"}]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.INFO)
        load_email_list_config(str(config_file))

        assert f"Successfully loaded 1 configuration entries from {config_file}" in caplog.text

    def test_load_config_non_string_email(self, tmp_path, caplog):
        """Test error handling when email is not a string."""
        config_file = tmp_path / "email_list.json"
        config_data = [{"email": 12345, "search_url": "https://youtube.com"}]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.WARNING)
        validated = load_email_list_config(str(config_file))
        assert len(validated) == 0
        assert "Entry at index 0 missing or invalid 'email' field" in caplog.text

    def test_load_config_non_string_url(self, tmp_path, caplog):
        """Test error handling when search_url is not a string."""
        config_file = tmp_path / "email_list.json"
        config_data = [{"email": "user@example.com", "search_url": 12345}]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.WARNING)
        validated = load_email_list_config(str(config_file))
        assert len(validated) == 0
        assert "Entry at index 0 missing or invalid 'search_url' field" in caplog.text

    def test_load_config_multiple_entries_partial_valid(self, tmp_path, caplog):
        """Test that validation continues and filters out invalid entries."""
        config_file = tmp_path / "email_list.json"
        config_data = [
            {"email": "user1@example.com", "search_url": "https://youtube.com/1"},
            {"email": "invalid_email", "search_url": "https://youtube.com/2"},  # Invalid email
            {"email": "user3@example.com", "search_url": "https://youtube.com/3"},
        ]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.WARNING)
        validated = load_email_list_config(str(config_file))
        assert len(validated) == 2 
        assert validated[0]["email"] == "user1@example.com"
        assert validated[1]["email"] == "user3@example.com"
        assert "Entry at index 1 has invalid email format" in caplog.text
