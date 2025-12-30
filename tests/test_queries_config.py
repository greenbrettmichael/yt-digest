import json
import logging

import pytest

from app import load_queries_config


class TestQueriesConfig:
    """Tests for loading and validating queries.json configuration."""

    def test_load_valid_config(self, tmp_path):
        """Test loading a valid configuration file."""
        config_file = tmp_path / "queries.json"
        config_data = [
            {"search_url": "https://www.youtube.com/results?search_query=python"},
            {"search_url": "https://www.youtube.com/results?search_query=ai"},
        ]
        config_file.write_text(json.dumps(config_data))

        result = load_queries_config(str(config_file))

        assert len(result) == 2
        assert result[0]["search_url"] == "https://www.youtube.com/results?search_query=python"
        assert result[1]["search_url"] == "https://www.youtube.com/results?search_query=ai"

    def test_load_config_strips_whitespace(self, tmp_path):
        """Test that URL fields are stripped of whitespace."""
        config_file = tmp_path / "queries.json"
        config_data = [{"search_url": "  https://youtube.com/search  "}]
        config_file.write_text(json.dumps(config_data))

        result = load_queries_config(str(config_file))

        assert result[0]["search_url"] == "https://youtube.com/search"

    def test_load_config_file_not_found(self):
        """Test error handling when configuration file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_queries_config("nonexistent_file.json")

    def test_load_config_invalid_json(self, tmp_path):
        """Test error handling for malformed JSON."""
        config_file = tmp_path / "queries.json"
        config_file.write_text("{invalid json content")

        with pytest.raises(ValueError, match="Invalid JSON in configuration file"):
            load_queries_config(str(config_file))

    def test_load_config_not_array(self, tmp_path):
        """Test error handling when JSON is not an array."""
        config_file = tmp_path / "queries.json"
        config_file.write_text('{"search_url": "https://youtube.com"}')

        with pytest.raises(ValueError, match="Configuration must be a JSON array"):
            load_queries_config(str(config_file))

    def test_load_config_entry_not_object(self, tmp_path):
        """Test error handling when an entry is not an object."""
        config_file = tmp_path / "queries.json"
        config_file.write_text('["string_entry"]')

        with pytest.raises(ValueError, match="Entry at index 0 must be an object"):
            load_queries_config(str(config_file))

    def test_load_config_missing_search_url_field(self, tmp_path, caplog):
        """Test error handling when search_url field is missing and no channel fields provided."""
        config_file = tmp_path / "queries.json"
        config_data = [{}]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.WARNING)
        validated = load_queries_config(str(config_file))
        assert len(validated) == 0
        assert "missing valid 'search_url' or channel field" in caplog.text

    def test_load_config_empty_search_url_field(self, tmp_path, caplog):
        """Test error handling when search_url field is empty and no channel fields provided."""
        config_file = tmp_path / "queries.json"
        config_data = [{"search_url": ""}]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.WARNING)
        validated = load_queries_config(str(config_file))
        assert len(validated) == 0
        assert "missing valid 'search_url' or channel field" in caplog.text

    def test_load_config_empty_array(self, tmp_path, caplog):
        """Test error handling when configuration array is empty."""
        config_file = tmp_path / "queries.json"
        config_file.write_text("[]")

        caplog.set_level(logging.WARNING)
        validated = load_queries_config(str(config_file))
        assert len(validated) == 0
        assert "Configuration file contains no valid entries" in caplog.text

    def test_load_config_logs_success(self, tmp_path, caplog):
        """Test that successful loading logs appropriate message."""
        config_file = tmp_path / "queries.json"
        config_data = [{"search_url": "https://youtube.com"}]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.INFO)
        load_queries_config(str(config_file))

        assert f"Successfully loaded 1 configuration entries from {config_file}" in caplog.text

    def test_load_config_non_string_url(self, tmp_path, caplog):
        """Test error handling when search_url is not a string and no channel fields provided."""
        config_file = tmp_path / "queries.json"
        config_data = [{"search_url": 12345}]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.WARNING)
        validated = load_queries_config(str(config_file))
        assert len(validated) == 0
        assert "missing valid 'search_url' or channel field" in caplog.text

    def test_load_config_multiple_entries_partial_valid(self, tmp_path, caplog):
        """Test that validation continues and filters out invalid entries."""
        config_file = tmp_path / "queries.json"
        config_data = [
            {"search_url": "https://youtube.com/1"},
            {},  # Invalid - no sources
            {"search_url": "https://youtube.com/3"},
        ]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.WARNING)
        validated = load_queries_config(str(config_file))
        assert len(validated) == 2
        assert validated[0]["search_url"] == "https://youtube.com/1"
        assert validated[1]["search_url"] == "https://youtube.com/3"

    def test_load_config_with_channel_id(self, tmp_path):
        """Test loading configuration with channel_id field."""
        config_file = tmp_path / "queries.json"
        config_data = [{"channel_id": "UC8butISFwT-Wl7EV0hUK0BQ"}]
        config_file.write_text(json.dumps(config_data))

        result = load_queries_config(str(config_file))

        assert len(result) == 1
        assert result[0]["channel_id"] == "UC8butISFwT-Wl7EV0hUK0BQ"
        assert "search_url" not in result[0]

    def test_load_config_with_channel_url(self, tmp_path):
        """Test loading configuration with channel_url field."""
        config_file = tmp_path / "queries.json"
        config_data = [{"channel_url": "https://www.youtube.com/@mkbhd"}]
        config_file.write_text(json.dumps(config_data))

        result = load_queries_config(str(config_file))

        assert len(result) == 1
        assert result[0]["channel_url"] == "https://www.youtube.com/@mkbhd"

    def test_load_config_with_channel_username(self, tmp_path):
        """Test loading configuration with channel_username field."""
        config_file = tmp_path / "queries.json"
        config_data = [{"channel_username": "LinusTechTips"}]
        config_file.write_text(json.dumps(config_data))

        result = load_queries_config(str(config_file))

        assert len(result) == 1
        assert result[0]["channel_username"] == "LinusTechTips"

    def test_load_config_with_multiple_sources(self, tmp_path):
        """Test loading configuration with both search_url and channel fields."""
        config_file = tmp_path / "queries.json"
        config_data = [
            {
                "search_url": "https://www.youtube.com/results?search_query=python",
                "channel_username": "LinusTechTips",
                "channel_id": "UC8butISFwT-Wl7EV0hUK0BQ",
            }
        ]
        config_file.write_text(json.dumps(config_data))

        result = load_queries_config(str(config_file))

        assert len(result) == 1
        assert result[0]["search_url"] == "https://www.youtube.com/results?search_query=python"
        assert result[0]["channel_username"] == "LinusTechTips"
        assert result[0]["channel_id"] == "UC8butISFwT-Wl7EV0hUK0BQ"

    def test_load_config_channel_only_no_search_url(self, tmp_path):
        """Test that entries with channel fields but no search_url are valid."""
        config_file = tmp_path / "queries.json"
        config_data = [{"channel_id": "UC123"}]
        config_file.write_text(json.dumps(config_data))

        result = load_queries_config(str(config_file))

        assert len(result) == 1
        assert "search_url" not in result[0]
        assert result[0]["channel_id"] == "UC123"

    def test_load_config_missing_all_sources(self, tmp_path, caplog):
        """Test that entries without search_url or channel fields are rejected."""
        config_file = tmp_path / "queries.json"
        config_data = [{}]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.WARNING)
        result = load_queries_config(str(config_file))

        assert len(result) == 0
        assert "missing valid 'search_url' or channel field" in caplog.text

    def test_load_config_empty_channel_fields(self, tmp_path, caplog):
        """Test that empty channel fields are ignored."""
        config_file = tmp_path / "queries.json"
        config_data = [{"channel_id": "", "channel_url": "   "}]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.WARNING)
        result = load_queries_config(str(config_file))

        assert len(result) == 0
        assert "missing valid 'search_url' or channel field" in caplog.text

    def test_load_config_strips_channel_whitespace(self, tmp_path):
        """Test that channel fields are stripped of whitespace."""
        config_file = tmp_path / "queries.json"
        config_data = [{"channel_username": "  LinusTechTips  "}]
        config_file.write_text(json.dumps(config_data))

        result = load_queries_config(str(config_file))

        assert result[0]["channel_username"] == "LinusTechTips"

    def test_load_config_non_string_channel_fields(self, tmp_path, caplog):
        """Test that non-string channel fields are ignored."""
        config_file = tmp_path / "queries.json"
        config_data = [{"channel_id": 12345}]
        config_file.write_text(json.dumps(config_data))

        caplog.set_level(logging.WARNING)
        result = load_queries_config(str(config_file))

        assert len(result) == 0
        assert "missing valid 'search_url' or channel field" in caplog.text
