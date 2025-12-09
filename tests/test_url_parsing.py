"""Tests for YouTube URL parsing functionality."""

from app import parse_youtube_search_input


class TestParseYoutubeSearchInput:
    """Tests for the parse_youtube_search_input function."""

    def test_plain_keyword(self):
        """Test that a plain keyword is returned as-is."""
        search_query, sp_param = parse_youtube_search_input("news")
        assert search_query == "news"
        assert sp_param is None

    def test_plain_keyword_with_spaces(self):
        """Test that a plain keyword with spaces is handled correctly."""
        search_query, sp_param = parse_youtube_search_input("python tutorials")
        assert search_query == "python tutorials"
        assert sp_param is None

    def test_url_with_search_query_only(self):
        """Test parsing a URL with only search_query parameter."""
        url = "https://www.youtube.com/results?search_query=news"
        search_query, sp_param = parse_youtube_search_input(url)
        assert search_query == "news"
        assert sp_param is None

    def test_url_with_search_query_and_sp(self):
        """Test parsing a URL with both search_query and sp parameters."""
        url = "https://www.youtube.com/results?search_query=news&sp=CAASBAgCEAE%3D"
        search_query, sp_param = parse_youtube_search_input(url)
        assert search_query == "news"
        # URL-encoded %3D is decoded to =
        assert sp_param == "CAASBAgCEAE="

    def test_url_with_encoded_search_query(self):
        """Test parsing a URL with URL-encoded search query."""
        url = "https://www.youtube.com/results?search_query=python+tutorials"
        search_query, sp_param = parse_youtube_search_input(url)
        assert search_query == "python tutorials"
        assert sp_param is None

    def test_url_with_multiple_parameters(self):
        """Test parsing a URL with multiple query parameters."""
        url = "https://www.youtube.com/results?search_query=news&sp=CAASBAgCEAE%3D&other=value"
        search_query, sp_param = parse_youtube_search_input(url)
        assert search_query == "news"
        assert sp_param == "CAASBAgCEAE="

    def test_url_without_search_query(self):
        """Test parsing a URL without search_query parameter (edge case)."""
        url = "https://www.youtube.com/results?sp=CAASBAgCEAE%3D"
        search_query, sp_param = parse_youtube_search_input(url)
        # Should return the full URL as search_query if search_query param is missing
        assert search_query == url
        assert sp_param == "CAASBAgCEAE="

    def test_url_starting_with_www(self):
        """Test parsing a URL that starts with www (no protocol)."""
        url = "www.youtube.com/results?search_query=test"
        search_query, sp_param = parse_youtube_search_input(url)
        assert search_query == "test"
        assert sp_param is None

    def test_malformed_url_treated_as_keyword(self):
        """Test that a malformed URL is treated as a plain keyword."""
        # This will fail URL parsing and fall back to treating it as a keyword
        malformed_url = "not-a-url-but-contains://something"
        search_query, sp_param = parse_youtube_search_input(malformed_url)
        # Should fall back to treating as keyword
        assert search_query == malformed_url
        assert sp_param is None

    def test_empty_string(self):
        """Test parsing an empty string."""
        search_query, sp_param = parse_youtube_search_input("")
        assert search_query == ""
        assert sp_param is None

    def test_url_with_fragment(self):
        """Test parsing a URL with a fragment identifier."""
        url = "https://www.youtube.com/results?search_query=news#top"
        search_query, sp_param = parse_youtube_search_input(url)
        assert search_query == "news"
        assert sp_param is None

    def test_special_characters_in_keyword(self):
        """Test that special characters in a plain keyword are preserved."""
        keyword = "C++ programming"
        search_query, sp_param = parse_youtube_search_input(keyword)
        assert search_query == "C++ programming"
        assert sp_param is None

    def test_url_with_complex_sp_parameter(self):
        """Test parsing a URL with a complex sp parameter value."""
        # Example of a real YouTube sp parameter
        url = "https://www.youtube.com/results?search_query=news&sp=EgQIBBAB"
        search_query, sp_param = parse_youtube_search_input(url)
        assert search_query == "news"
        assert sp_param == "EgQIBBAB"
