import xml.etree.ElementTree as ET

import pytest

from app import generate_rss_feed


class TestRSSFeedGeneration:
    """Tests for RSS feed generation."""

    def test_generate_rss_feed_basic(self, tmp_path):
        """Test basic RSS feed generation with one entry."""
        output_file = tmp_path / "test_feed.xml"
        summaries = [
            {
                "title": "Test Video 1",
                "video_id": "test123",
                "summary": "This is a test summary.",
                "timestamp": "Mon, 01 Jan 2024 12:00:00 GMT"
            }
        ]

        generate_rss_feed(summaries, str(output_file))

        assert output_file.exists()

        # Parse and validate XML
        tree = ET.parse(str(output_file))
        root = tree.getroot()

        assert root.tag == "rss"
        assert root.attrib["version"] == "2.0"

        channel = root.find("channel")
        assert channel is not None

        # Check channel metadata
        assert channel.find("title").text == "YouTube Digest Feed"
        assert channel.find("description").text == "AI-powered summaries of YouTube videos"

        # Check items
        items = channel.findall("item")
        assert len(items) == 1

        item = items[0]
        assert item.find("title").text == "Test Video 1"
        assert item.find("link").text == "https://www.youtube.com/watch?v=test123"
        assert item.find("guid").text == "test123"
        assert item.find("pubDate").text == "Mon, 01 Jan 2024 12:00:00 GMT"

    def test_generate_rss_feed_multiple_entries(self, tmp_path):
        """Test RSS feed generation with multiple entries."""
        output_file = tmp_path / "test_feed.xml"
        summaries = [
            {
                "title": "Video 1",
                "video_id": "vid1",
                "summary": "Summary 1",
                "timestamp": "Mon, 01 Jan 2024 12:00:00 GMT"
            },
            {
                "title": "Video 2",
                "video_id": "vid2",
                "summary": "Summary 2",
                "timestamp": "Tue, 02 Jan 2024 12:00:00 GMT"
            },
            {
                "title": "Video 3",
                "video_id": "vid3",
                "summary": "Summary 3",
                "timestamp": "Wed, 03 Jan 2024 12:00:00 GMT"
            }
        ]

        generate_rss_feed(summaries, str(output_file))

        tree = ET.parse(str(output_file))
        root = tree.getroot()
        channel = root.find("channel")
        items = channel.findall("item")

        assert len(items) == 3
        assert items[0].find("title").text == "Video 1"
        assert items[1].find("title").text == "Video 2"
        assert items[2].find("title").text == "Video 3"

    def test_generate_rss_feed_overwrites_existing(self, tmp_path):
        """Test that RSS feed overwrites existing file."""
        output_file = tmp_path / "test_feed.xml"

        # Create initial feed
        summaries1 = [
            {
                "title": "Old Video",
                "video_id": "old123",
                "summary": "Old summary",
                "timestamp": "Mon, 01 Jan 2024 12:00:00 GMT"
            }
        ]
        generate_rss_feed(summaries1, str(output_file))

        # Overwrite with new feed
        summaries2 = [
            {
                "title": "New Video",
                "video_id": "new123",
                "summary": "New summary",
                "timestamp": "Tue, 02 Jan 2024 12:00:00 GMT"
            }
        ]
        generate_rss_feed(summaries2, str(output_file))

        # Verify only new content exists
        tree = ET.parse(str(output_file))
        root = tree.getroot()
        channel = root.find("channel")
        items = channel.findall("item")

        assert len(items) == 1
        assert items[0].find("title").text == "New Video"
        # Verify the guid changed (old video ID should not be present)
        assert items[0].find("guid").text == "new123"

    def test_generate_rss_feed_truncates_long_summary(self, tmp_path):
        """Test that very long summaries are truncated."""
        output_file = tmp_path / "test_feed.xml"

        # Create a summary that exceeds MAX_SUMMARY_LENGTH (10000 chars)
        long_summary = "A" * 15000

        summaries = [
            {
                "title": "Long Video",
                "video_id": "long123",
                "summary": long_summary,
                "timestamp": "Mon, 01 Jan 2024 12:00:00 GMT"
            }
        ]

        generate_rss_feed(summaries, str(output_file))

        tree = ET.parse(str(output_file))
        root = tree.getroot()
        channel = root.find("channel")
        items = channel.findall("item")

        assert len(items) == 1
        description = items[0].find("description").text

        # Should be truncated and contain truncation message
        assert len(description) < 15000
        assert "[Summary truncated due to length]" in description

    def test_generate_rss_feed_empty_summaries(self, tmp_path):
        """Test RSS feed generation with no summaries."""
        output_file = tmp_path / "test_feed.xml"
        summaries = []

        generate_rss_feed(summaries, str(output_file))

        tree = ET.parse(str(output_file))
        root = tree.getroot()
        channel = root.find("channel")
        items = channel.findall("item")

        assert len(items) == 0

    def test_generate_rss_feed_special_characters(self, tmp_path):
        """Test RSS feed handles special characters in titles and summaries."""
        output_file = tmp_path / "test_feed.xml"
        summaries = [
            {
                "title": "Video with <special> & 'characters'",
                "video_id": "special123",
                "summary": "Summary with <tags> & entities",
                "timestamp": "Mon, 01 Jan 2024 12:00:00 GMT"
            }
        ]

        generate_rss_feed(summaries, str(output_file))

        # Should not raise parsing error
        tree = ET.parse(str(output_file))
        root = tree.getroot()
        channel = root.find("channel")
        items = channel.findall("item")

        assert len(items) == 1

    def test_generate_rss_feed_io_error(self, tmp_path):
        """Test error handling when file cannot be written."""
        # Try to write to a directory that doesn't exist
        output_file = tmp_path / "nonexistent_dir" / "feed.xml"

        summaries = [
            {
                "title": "Test",
                "video_id": "test",
                "summary": "Test",
                "timestamp": "Mon, 01 Jan 2024 12:00:00 GMT"
            }
        ]

        with pytest.raises(OSError):
            generate_rss_feed(summaries, str(output_file))
