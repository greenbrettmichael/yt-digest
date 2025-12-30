from unittest.mock import patch

from app import get_channel_videos_last_day, is_video_within_last_day


class TestIsVideoWithinLastDay:
    """Tests for the is_video_within_last_day function."""

    def test_video_from_minutes_ago(self):
        """Test that videos from minutes ago are within the last day."""
        video = {"publishedTimeText": {"simpleText": "30 minutes ago"}}
        assert is_video_within_last_day(video) is True

    def test_video_from_hours_ago(self):
        """Test that videos from hours ago are within the last day."""
        video = {"publishedTimeText": {"simpleText": "5 hours ago"}}
        assert is_video_within_last_day(video) is True

    def test_video_from_one_day_ago(self):
        """Test that videos from 1 day ago are within the last day."""
        video = {"publishedTimeText": {"simpleText": "1 day ago"}}
        assert is_video_within_last_day(video) is True

    def test_video_from_two_days_ago(self):
        """Test that videos from 2 days ago are not within the last day."""
        video = {"publishedTimeText": {"simpleText": "2 days ago"}}
        assert is_video_within_last_day(video) is False

    def test_video_from_weeks_ago(self):
        """Test that videos from weeks ago are not within the last day."""
        video = {"publishedTimeText": {"simpleText": "2 weeks ago"}}
        assert is_video_within_last_day(video) is False

    def test_video_from_months_ago(self):
        """Test that videos from months ago are not within the last day."""
        video = {"publishedTimeText": {"simpleText": "3 months ago"}}
        assert is_video_within_last_day(video) is False

    def test_video_missing_published_time(self):
        """Test that videos missing publish time return False."""
        video = {"videoId": "test123"}
        assert is_video_within_last_day(video) is False

    def test_video_empty_published_text(self):
        """Test that videos with empty publish text return False."""
        video = {"publishedTimeText": {"simpleText": ""}}
        assert is_video_within_last_day(video) is False

    def test_video_malformed_published_text(self):
        """Test that videos with malformed publish text return False."""
        video = {"publishedTimeText": {"simpleText": "invalid format"}}
        assert is_video_within_last_day(video) is False


class TestGetChannelVideosLastDay:
    """Tests for the get_channel_videos_last_day function."""

    @patch("app.scrapetube.get_channel")
    def test_get_channel_videos_by_id(self, mock_get_channel, mock_api_client):
        """Test fetching channel videos using channel_id."""
        # Setup mock videos - 2 recent, 1 old
        recent_video_1 = {
            "videoId": "vid_1",
            "title": {"runs": [{"text": "Recent Video 1"}]},
            "publishedTimeText": {"simpleText": "2 hours ago"},
        }
        recent_video_2 = {
            "videoId": "vid_2",
            "title": {"runs": [{"text": "Recent Video 2"}]},
            "publishedTimeText": {"simpleText": "12 hours ago"},
        }
        old_video = {
            "videoId": "vid_3",
            "title": {"runs": [{"text": "Old Video"}]},
            "publishedTimeText": {"simpleText": "3 days ago"},
        }

        mock_get_channel.return_value = iter([recent_video_1, recent_video_2, old_video])

        # Execute
        results = get_channel_videos_last_day(channel_id="UC123", api_client=mock_api_client)

        # Verify
        assert len(results) == 2
        assert results[0]["video_id"] == "vid_1"
        assert results[0]["title"] == "Recent Video 1"
        assert results[1]["video_id"] == "vid_2"
        assert results[1]["title"] == "Recent Video 2"

        # Verify get_channel was called correctly
        mock_get_channel.assert_called_once_with(
            channel_id="UC123", channel_url=None, channel_username=None, sort_by="newest", sleep=1
        )

    @patch("app.scrapetube.get_channel")
    def test_get_channel_videos_by_username(self, mock_get_channel, mock_api_client):
        """Test fetching channel videos using channel_username."""
        recent_video = {
            "videoId": "vid_1",
            "title": {"runs": [{"text": "Test Video"}]},
            "publishedTimeText": {"simpleText": "5 hours ago"},
        }

        mock_get_channel.return_value = iter([recent_video])

        # Execute
        results = get_channel_videos_last_day(channel_username="LinusTechTips", api_client=mock_api_client)

        # Verify
        assert len(results) == 1
        assert results[0]["video_id"] == "vid_1"

        # Verify get_channel was called with username
        mock_get_channel.assert_called_once_with(
            channel_id=None, channel_url=None, channel_username="LinusTechTips", sort_by="newest", sleep=1
        )

    @patch("app.scrapetube.get_channel")
    def test_get_channel_videos_by_url(self, mock_get_channel, mock_api_client):
        """Test fetching channel videos using channel_url."""
        recent_video = {
            "videoId": "vid_1",
            "title": {"runs": [{"text": "Test Video"}]},
            "publishedTimeText": {"simpleText": "30 minutes ago"},
        }

        mock_get_channel.return_value = iter([recent_video])

        # Execute
        results = get_channel_videos_last_day(
            channel_url="https://www.youtube.com/@mkbhd", api_client=mock_api_client
        )

        # Verify
        assert len(results) == 1
        mock_get_channel.assert_called_once_with(
            channel_id=None, channel_url="https://www.youtube.com/@mkbhd", channel_username=None, sort_by="newest", sleep=1
        )

    @patch("app.scrapetube.get_channel")
    def test_no_recent_videos(self, mock_get_channel, mock_api_client):
        """Test when channel has no videos from the last 24 hours."""
        old_video = {
            "videoId": "vid_1",
            "title": {"runs": [{"text": "Old Video"}]},
            "publishedTimeText": {"simpleText": "5 days ago"},
        }

        mock_get_channel.return_value = iter([old_video])

        # Execute
        results = get_channel_videos_last_day(channel_id="UC123", api_client=mock_api_client)

        # Verify
        assert len(results) == 0

    @patch("app.scrapetube.get_channel")
    def test_transcript_disabled_skipped(self, mock_get_channel, mock_api_client):
        """Test that videos with disabled transcripts are skipped."""
        from youtube_transcript_api import TranscriptsDisabled

        recent_video = {
            "videoId": "vid_1",
            "title": {"runs": [{"text": "Test Video"}]},
            "publishedTimeText": {"simpleText": "2 hours ago"},
        }

        mock_get_channel.return_value = iter([recent_video])
        mock_api_client.list.side_effect = TranscriptsDisabled("vid_1")

        # Execute
        results = get_channel_videos_last_day(channel_id="UC123", api_client=mock_api_client)

        # Verify - should return empty list since transcript is disabled
        assert len(results) == 0

    @patch("app.scrapetube.get_channel")
    def test_error_fetching_channel_returns_empty_list(self, mock_get_channel, mock_api_client):
        """Test that errors in fetching channel videos return an empty list."""
        mock_get_channel.side_effect = Exception("Channel not found")

        # Execute
        results = get_channel_videos_last_day(channel_id="UC123", api_client=mock_api_client)

        # Verify
        assert len(results) == 0

    @patch("app.scrapetube.get_channel")
    def test_video_with_bad_title_structure(self, mock_get_channel, mock_api_client):
        """Test that videos with malformed titles get 'Unknown Title'."""
        bad_video = {
            "videoId": "vid_bad",
            "title": {},
            "publishedTimeText": {"simpleText": "1 hour ago"},
        }

        mock_get_channel.return_value = iter([bad_video])

        # Execute
        results = get_channel_videos_last_day(channel_id="UC123", api_client=mock_api_client)

        # Verify
        assert len(results) == 1
        assert results[0]["title"] == "Unknown Title"
