import logging
from unittest.mock import mock_open, patch

import pytest

from app import save_results_to_json


class TestJsonOutput:
    """Tests for the JSON file writing functionality."""

    def test_save_results_to_json_success(self, caplog):
        fake_data = [{"video_id": "123", "title": "Test", "transcript": "Content"}]
        filename = "test_output.json"

        # Ensure we capture INFO logs
        caplog.set_level(logging.INFO)

        with patch("builtins.open", mock_open()) as mocked_file, patch("json.dump") as mocked_dump:
            save_results_to_json(fake_data, filename)

            # 1. Verify file operations
            mocked_file.assert_called_once_with(filename, "w", encoding="utf-8")
            mocked_dump.assert_called_once_with(fake_data, mocked_file(), indent=4, ensure_ascii=False)

            # 2. Verify Success Log using caplog
            assert f"Successfully saved {len(fake_data)} records to {filename}" in caplog.text

    def test_save_results_io_error(self, caplog):
        """Test that the function logs the error AND re-raises the exception."""
        fake_data: list[dict] = []
        filename = "bad_file.json"

        # Ensure we capture ERROR logs
        caplog.set_level(logging.ERROR)

        # Simulate a permission denied error
        with patch("builtins.open", mock_open()) as mocked_file:
            mocked_file.side_effect = OSError("Permission denied")

            # 1. Verify that the exception is re-raised
            with pytest.raises(OSError):
                save_results_to_json(fake_data, filename)

            # 2. Verify the log message was captured by caplog
            # The log message in your function: f"Failed to write to file {filename}: {type(e).__name__}: {e}"
            assert f"Failed to write to file {filename}" in caplog.text
            assert "Permission denied" in caplog.text
