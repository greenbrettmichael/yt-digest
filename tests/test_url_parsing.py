"""Tests for YouTube URL parsing functionality."""

from app import decode_sp_parameter, parse_youtube_search_input


class TestDecodeSpParameter:
    """Tests for the decode_sp_parameter function."""

    def test_decode_relevance(self):
        """Test decoding sp parameter for relevance sort."""
        # CAASBAgCEAE= is relevance (A)
        sort_by = decode_sp_parameter("CAASBAgCEAE=")
        assert sort_by == "relevance"

    def test_decode_upload_date(self):
        """Test decoding sp parameter for upload_date sort."""
        # CAISAhAB is upload_date (I)
        sort_by = decode_sp_parameter("CAISAhAB")
        assert sort_by == "upload_date"

    def test_decode_view_count(self):
        """Test decoding sp parameter for view_count sort."""
        # CAMSAhAB is view_count (M)
        sort_by = decode_sp_parameter("CAMSAhAB")
        assert sort_by == "view_count"

    def test_decode_rating(self):
        """Test decoding sp parameter for rating sort."""
        # CAESAhAB is rating (E)
        sort_by = decode_sp_parameter("CAESAhAB")
        assert sort_by == "rating"

    def test_decode_unknown_code(self):
        """Test decoding sp parameter with unknown sort code."""
        # CAX would have unknown sort code X
        sort_by = decode_sp_parameter("CAXSAhAB")
        assert sort_by is None

    def test_decode_malformed_sp(self):
        """Test decoding malformed sp parameter."""
        sort_by = decode_sp_parameter("INVALID")
        assert sort_by is None

    def test_decode_empty_sp(self):
        """Test decoding empty sp parameter."""
        sort_by = decode_sp_parameter("")
        assert sort_by is None


class TestParseYoutubeSearchInput:
    """Tests for the parse_youtube_search_input function."""

    def test_plain_keyword(self):
        """Test that a plain keyword is returned as-is."""
        search_query, sort_by = parse_youtube_search_input("news")
        assert search_query == "news"
        assert sort_by is None

    def test_plain_keyword_with_spaces(self):
        """Test that a plain keyword with spaces is handled correctly."""
        search_query, sort_by = parse_youtube_search_input("python tutorials")
        assert search_query == "python tutorials"
        assert sort_by is None

    def test_url_with_search_query_only(self):
        """Test parsing a URL with only search_query parameter."""
        url = "https://www.youtube.com/results?search_query=news"
        search_query, sort_by = parse_youtube_search_input(url)
        assert search_query == "news"
        assert sort_by is None

    def test_url_with_search_query_and_sp_relevance(self):
        """Test parsing a URL with both search_query and sp parameters (relevance)."""
        url = "https://www.youtube.com/results?search_query=news&sp=CAASBAgCEAE%3D"
        search_query, sort_by = parse_youtube_search_input(url)
        assert search_query == "news"
        assert sort_by == "relevance"

    def test_url_with_sp_upload_date(self):
        """Test parsing a URL with sp parameter for upload_date."""
        url = "https://www.youtube.com/results?search_query=news&sp=CAISAhAB"
        search_query, sort_by = parse_youtube_search_input(url)
        assert search_query == "news"
        assert sort_by == "upload_date"

    def test_url_with_sp_view_count(self):
        """Test parsing a URL with sp parameter for view_count."""
        url = "https://www.youtube.com/results?search_query=news&sp=CAMSAhAB"
        search_query, sort_by = parse_youtube_search_input(url)
        assert search_query == "news"
        assert sort_by == "view_count"

    def test_url_with_sp_rating(self):
        """Test parsing a URL with sp parameter for rating."""
        url = "https://www.youtube.com/results?search_query=news&sp=CAESAhAB"
        search_query, sort_by = parse_youtube_search_input(url)
        assert search_query == "news"
        assert sort_by == "rating"

    def test_url_with_encoded_search_query(self):
        """Test parsing a URL with URL-encoded search query."""
        url = "https://www.youtube.com/results?search_query=python+tutorials"
        search_query, sort_by = parse_youtube_search_input(url)
        assert search_query == "python tutorials"
        assert sort_by is None

    def test_url_with_multiple_parameters(self):
        """Test parsing a URL with multiple query parameters."""
        url = "https://www.youtube.com/results?search_query=news&sp=CAASBAgCEAE%3D&other=value"
        search_query, sort_by = parse_youtube_search_input(url)
        assert search_query == "news"
        assert sort_by == "relevance"

    def test_url_without_search_query(self):
        """Test parsing a URL without search_query parameter (edge case)."""
        url = "https://www.youtube.com/results?sp=CAASBAgCEAE%3D"
        search_query, sort_by = parse_youtube_search_input(url)
        # Should return the full URL as search_query if search_query param is missing
        assert search_query == url
        assert sort_by == "relevance"

    def test_url_starting_with_www(self):
        """Test parsing a URL that starts with www (no protocol)."""
        url = "www.youtube.com/results?search_query=test"
        search_query, sort_by = parse_youtube_search_input(url)
        assert search_query == "test"
        assert sort_by is None

    def test_malformed_url_treated_as_keyword(self):
        """Test that a malformed URL is treated as a plain keyword."""
        # This will fail URL parsing and fall back to treating it as a keyword
        malformed_url = "not-a-url-but-contains://something"
        search_query, sort_by = parse_youtube_search_input(malformed_url)
        # Should fall back to treating as keyword
        assert search_query == malformed_url
        assert sort_by is None

    def test_empty_string(self):
        """Test parsing an empty string."""
        search_query, sort_by = parse_youtube_search_input("")
        assert search_query == ""
        assert sort_by is None

    def test_url_with_fragment(self):
        """Test parsing a URL with a fragment identifier."""
        url = "https://www.youtube.com/results?search_query=news#top"
        search_query, sort_by = parse_youtube_search_input(url)
        assert search_query == "news"
        assert sort_by is None

    def test_special_characters_in_keyword(self):
        """Test that special characters in a plain keyword are preserved."""
        keyword = "C++ programming"
        search_query, sort_by = parse_youtube_search_input(keyword)
        assert search_query == "C++ programming"
        assert sort_by is None

    def test_url_with_unknown_sp_parameter(self):
        """Test parsing a URL with an unknown sp parameter pattern."""
        # EgQIBBAB doesn't follow the CA{code}SAhA{code} pattern
        url = "https://www.youtube.com/results?search_query=news&sp=EgQIBBAB"
        search_query, sort_by = parse_youtube_search_input(url)
        assert search_query == "news"
        # Should return None when sp cannot be decoded
        assert sort_by is None
