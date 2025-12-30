import json
import logging
import os
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement

import markdown
import scrapetube
from dotenv import load_dotenv
from openai import OpenAI
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig

# YouTube API constants for scrapetube's get_videos function
YOUTUBE_SEARCH_API_ENDPOINT = "https://www.youtube.com/youtubei/v1/search"
YOUTUBE_SEARCH_SELECTOR_LIST = "contents"
YOUTUBE_SEARCH_SELECTOR_ITEM = "videoRenderer"
YOUTUBE_SEARCH_SLEEP_SECONDS = 1


def get_transcript_api() -> YouTubeTranscriptApi:
    """
    Initializes and returns an instance of YouTubeTranscriptApi.
    If proxy credentials are found in environment variables, it configures the API to use the proxy.

    Returns:
        YouTubeTranscriptApi: An instance of the transcript API, possibly configured with a proxy.
    """
    load_dotenv()

    proxy_user = os.getenv("PROXY_USERNAME")
    proxy_pass = os.getenv("PROXY_PASSWORD")

    if not proxy_user or not proxy_pass:
        raise ValueError("Error: Proxy credentials not found in .env file")

    ytt_api = YouTubeTranscriptApi(
        proxy_config=WebshareProxyConfig(
            proxy_username=proxy_user,
            proxy_password=proxy_pass,
        )
    )
    return ytt_api


def load_queries_config(config_path: str = "queries.json") -> list[dict]:
    """
    Loads and validates the queries configuration from a JSON file.

    Args:
        config_path (str): Path to the queries.json configuration file.

    Returns:
        list[dict]: A list of validated configuration entries, each containing:
            - search_url (str, optional): YouTube search URL
            - channel_id (str, optional): YouTube channel ID
            - channel_url (str, optional): YouTube channel URL
            - channel_username (str, optional): YouTube channel username

    Note:
        Each entry must have either a search_url OR at least one channel field
        (channel_id, channel_url, or channel_username).

    Raises:
        FileNotFoundError: If the configuration file doesn't exist.
        ValueError: If the JSON is malformed or entries are missing required fields.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, encoding="utf-8") as f:
            config_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {e}")

    if not isinstance(config_data, list):
        raise ValueError("Configuration must be a JSON array of objects")

    validated_entries = []
    for idx, entry in enumerate(config_data):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry at index {idx} must be an object")

        search_url = entry.get("search_url")
        channel_id = entry.get("channel_id")
        channel_url = entry.get("channel_url")
        channel_username = entry.get("channel_username")

        # Validate that at least one source is provided (search_url OR channel)
        has_search_url = search_url and isinstance(search_url, str) and search_url.strip()
        has_channel_id = channel_id and isinstance(channel_id, str) and channel_id.strip()
        has_channel_url = channel_url and isinstance(channel_url, str) and channel_url.strip()
        has_channel_username = channel_username and isinstance(channel_username, str) and channel_username.strip()

        if not (has_search_url or has_channel_id or has_channel_url or has_channel_username):
            logging.warning(
                f"Entry at index {idx} missing valid 'search_url' or channel field "
                "(channel_id, channel_url, or channel_username)"
            )
            continue

        # Build validated entry
        validated_entry = {}
        # Additional checks help mypy understand these are not None
        if has_search_url and search_url:
            validated_entry["search_url"] = search_url.strip()
        if has_channel_id and channel_id:
            validated_entry["channel_id"] = channel_id.strip()
        if has_channel_url and channel_url:
            validated_entry["channel_url"] = channel_url.strip()
        if has_channel_username and channel_username:
            validated_entry["channel_username"] = channel_username.strip()

        validated_entries.append(validated_entry)

    if len(validated_entries) == 0:
        logging.warning("Configuration file contains no valid entries")
        return []

    logging.info(f"Successfully loaded {len(validated_entries)} configuration entries from {config_path}")
    return validated_entries


def is_video_within_last_day(video: dict) -> bool:
    """
    Checks if a video was published within the last 24 hours.

    Args:
        video (dict): A video dictionary from scrapetube containing publishedTimeText.

    Returns:
        bool: True if the video was published within the last 24 hours, False otherwise.
    """
    try:
        published_text = video.get("publishedTimeText", {}).get("simpleText", "")
        if not published_text:
            return False

        # Parse relative time strings like "2 hours ago", "1 day ago", etc.
        published_text_lower = published_text.lower()

        # Check for videos from within the last day
        if "minute" in published_text_lower or "hour" in published_text_lower:
            return True
        elif "day" in published_text_lower:
            # Extract the number of days
            parts = published_text_lower.split()
            try:
                num_days = int(parts[0])
                return num_days <= 1
            except (ValueError, IndexError):
                return False
        else:
            # Anything else (weeks, months, years) is not within the last day
            return False
    except Exception as e:
        logging.warning(f"Error parsing video publish date: {e}")
        return False


def get_channel_videos_last_day(
    channel_id: str | None = None,
    channel_url: str | None = None,
    channel_username: str | None = None,
    api_client: YouTubeTranscriptApi | None = None,
) -> list[dict]:
    """
    Retrieves videos from a channel that were published within the last 24 hours.

    Args:
        channel_id (str, optional): The YouTube channel ID.
        channel_url (str, optional): The YouTube channel URL.
        channel_username (str, optional): The YouTube channel username (without @).
        api_client (YouTubeTranscriptApi, optional): An instance of YouTubeTranscriptApi.

    Returns:
        list[dict]: List of dictionaries containing video_id, title, and transcript.
    """
    channel_identifier = channel_id or channel_url or channel_username
    logging.info(f"Fetching videos from channel: {channel_identifier}")

    try:
        # Get videos from the channel, sorted by newest first
        # Note: Using scrapetube.get_channel() (top-level API) instead of
        # scrapetube.scrapetube.get_videos() (lower-level function) for channel queries
        channel_videos = scrapetube.get_channel(
            channel_id=channel_id,
            channel_url=channel_url,
            channel_username=channel_username,
            sort_by="newest",
            sleep=YOUTUBE_SEARCH_SLEEP_SECONDS,
        )

        # Filter videos from the last 24 hours
        recent_videos = []
        for video in channel_videos:
            if is_video_within_last_day(video):
                recent_videos.append(video)
            else:
                # Since videos are sorted by newest, we can stop once we hit an older video
                break

        logging.info(f"Found {len(recent_videos)} videos from the last 24 hours for channel: {channel_identifier}")

        # Process transcripts for the recent videos
        results_data = []
        transcript_api = api_client or get_transcript_api()

        for video in recent_videos:
            video_id = video.get("videoId")
            try:
                title = video["title"]["runs"][0]["text"]
            except (KeyError, IndexError):
                title = "Unknown Title"

            logging.info(f"Processing channel video: {title} [{video_id}]")

            try:
                transcript_list_obj = transcript_api.list(video_id)

                # Try to find English variants first
                try:
                    transcript_obj = transcript_list_obj.find_transcript(["en", "en-US", "en-GB"])
                    logging.info(
                        f"Found English transcript for video ID: {video_id} with language code: {transcript_obj.language_code}"
                    )
                except:
                    # Fallback: If no English, just take the first available one
                    transcript_obj = next(iter(transcript_list_obj))
                    logging.info(
                        f"No English transcript found. Using available transcript with language code: {transcript_obj.language_code} for video ID: {video_id}"
                    )

                # fetch() returns a list of dictionaries with 'text', 'start', and 'duration'
                fetched_transcript = transcript_obj.fetch()

                # Preserve transcript items with timestamps
                transcript_items = [{"text": item.text, "start": item.start} for item in fetched_transcript]

            except TranscriptsDisabled:
                logging.info(f"Transcripts are disabled for video ID: {video_id}")
                continue
            except NoTranscriptFound:
                logging.info(f"No transcript found for video ID: {video_id}.")
                continue
            except Exception as e:
                logging.info(f"Error retrieving transcript for video ID: {video_id}: {str(e)}")
                continue

            results_data.append({"video_id": video_id, "title": title, "transcript": transcript_items})

        return results_data

    except Exception as e:
        logging.error(f"Error fetching channel videos: {e}")
        return []


def get_recent_transcripts(url: str, limit: int = 10, api_client: YouTubeTranscriptApi | None = None) -> list[dict]:
    """
    Searches for the most recent videos by URL and retrieves their transcripts.

    Args:
        url (str):  A full YouTube search URL with optional sp parameter for advanced filtering
        limit (int): The maximum number of videos to process.
        api_client (YouTubeTranscriptApi, optional): An instance of YouTubeTranscriptApi. If None, a new instance will be created.
    Returns:
        List of dictionaries, each containing:
            - video_id (str): The YouTube video ID
            - title (str): The video title
            - transcript (list[dict]): List of transcript segments, each with 'text' (str) and 'start' (float) keys
    """

    logging.info(f"Using YouTube search URL: {url}")
    search_results = scrapetube.scrapetube.get_videos(
        url=url,
        api_endpoint=YOUTUBE_SEARCH_API_ENDPOINT,
        selector_list=YOUTUBE_SEARCH_SELECTOR_LIST,
        selector_item=YOUTUBE_SEARCH_SELECTOR_ITEM,
        limit=limit,
        sleep=YOUTUBE_SEARCH_SLEEP_SECONDS,
    )

    videos_processed = 0
    results_data = []
    transcript_api = api_client or get_transcript_api()

    for video in search_results:
        video_id = video.get("videoId")
        try:
            title = video["title"]["runs"][0]["text"]
        except (KeyError, IndexError):
            title = "Unknown Title"

        logging.info(f"Processing ({videos_processed + 1}/{limit}): {title} [{video_id}]")
        videos_processed += 1

        try:
            transcript_list_obj = transcript_api.list(video_id)

            # Try to find English variants first
            try:
                transcript_obj = transcript_list_obj.find_transcript(["en", "en-US", "en-GB"])
                logging.info(
                    f"Found English transcript for video ID: {video_id} with language code: {transcript_obj.language_code}"
                )
            except:
                # Fallback: If no English, just take the first available one (e.g., Spanish, Auto-generated, etc.)
                transcript_obj = next(iter(transcript_list_obj))
                logging.info(
                    f"No English transcript found. Using available transcript with language code: {transcript_obj.language_code} for video ID: {video_id}"
                )

            # fetch() returns a list of dictionaries with 'text', 'start', and 'duration'
            fetched_transcript = transcript_obj.fetch()

            # Preserve transcript items with timestamps
            transcript_items = [{"text": item.text, "start": item.start} for item in fetched_transcript]

        except TranscriptsDisabled:
            logging.info(f"Transcripts are disabled for video ID: {video_id}")
            continue
        except NoTranscriptFound:
            logging.info(f"No transcript found for video ID: {video_id}.")
            continue
        except Exception as e:
            logging.info(f"Error retrieving transcript for video ID: {video_id}: {str(e)}")
            continue

        results_data.append({"video_id": video_id, "title": title, "transcript": transcript_items})

    return results_data


def save_results_to_json(results: list[dict], filename: str):
    """
    Saves the list of transcript dictionaries to a JSON file.

    Args:
        results (list[dict]): The list of dictionaries from get_recent_transcripts.
        filename (str): The output filename.
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            # indent=4 makes it pretty. ensure_ascii=False keeps emojis/foreign chars readable.
            json.dump(results, f, indent=4, ensure_ascii=False)
        logging.info(f"Successfully saved {len(results)} records to {filename}")
    except OSError as e:
        logging.error(f"Failed to write to file {filename}: {type(e).__name__}: {e}")
        raise


def generate_newsletter_digest(json_data: list[dict], model: str = "gpt-5-mini-2025-08-07") -> str:
    """
    Sends transcript data to OpenAI to generate a newsletter digest for each video.

    Args:
        json_data (list[dict]): The list of video dictionaries.
        model (str): The OpenAI model to use (default: "gpt-5-mini-2025-08-07").

    Returns:
        str: The generated markdown newsletter.

    Raises:
        RuntimeError: If the OpenAI API call fails.
        ValueError: If the OPENAI_API_KEY environment variable is not set.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    client = OpenAI(api_key=api_key)

    # Truncate transcript to avoid overly long prompts and protect against large lists
    # Limit to max 15000 characters per transcript to handle large queries.json files
    max_transcript_length = 15000

    # Pre-process the data
    # We construct a string where we label every transcript clearly.
    context_block = ""
    for i, item in enumerate(json_data, 1):
        # We include the ID so the LLM can generate YouTube links
        context_block += f"--- VIDEO {i} ---\n"
        context_block += f"Title: {item['title']}\n"
        context_block += f"Video ID: {item['video_id']}\n"

        # Format transcript with timestamps
        transcript_data = item['transcript']
        if isinstance(transcript_data, list):
            # New format: list of dicts with text and start time
            segments = []
            for segment in transcript_data:
                # Validate segment structure
                if not isinstance(segment, dict):
                    logging.warning("Skipping transcript segment with unexpected type: %r", type(segment))
                    continue

                start = segment.get("start")
                text = segment.get("text")
                if start is None or text is None:
                    logging.warning("Skipping transcript segment missing 'start' or 'text': %r", segment)
                    continue

                try:
                    timestamp_seconds = round(float(start))
                except (TypeError, ValueError):
                    logging.warning("Skipping transcript segment with non-numeric 'start': %r", segment)
                    continue

                segments.append(f"[{timestamp_seconds}s] {text} ")

            transcript_formatted = "".join(segments)
            # Truncate to avoid overly long prompts
            transcript_formatted = transcript_formatted[:max_transcript_length]
            context_block += f"Transcript (with timestamps in seconds): {transcript_formatted}\n\n"
        else:
            # Fallback for old format: plain text string (with type safety)
            if isinstance(transcript_data, str):
                safe_transcript = transcript_data
            else:
                logging.warning(
                    "Unexpected transcript_data type %s for video %s; coercing to string.",
                    type(transcript_data),
                    item.get("video_id"),
                )
                safe_transcript = "" if transcript_data is None else str(transcript_data)
            context_block += f"Transcript: {safe_transcript[:max_transcript_length]}\n\n"

    # Define the System Prompt
    system_prompt = (
        "You are an expert tech newsletter editor. Your goal is to synthesize "
        "raw video transcripts into a concise, high-value weekly digest."
    )

    # Define the User Prompt
    user_prompt = f"""
    Here are the transcripts from the most recent videos with timestamps.

    Please write a summary for the video in Markdown format.

    **Strict Formatting Rules:**
    1. Do NOT include a title, headline, or "Title:" line at the top.
    2. Do NOT include a link to the video.
    3. Do NOT include an Executive Summary or Intro.
    4. Start directly with "Key Takeaways:" as the first line.
    5. Do NOT include a "TL;DR" line.
    6. Do NOT include any concluding remarks, "If you want...", or offers for further instructions at the end.

    **Structure:**
    Key Takeaways:

    - **[MM:SS](https://www.youtube.com/watch?v=<Video ID>&t=<seconds>s)** - <Bullet 1: Specific, actionable detail>
    - **[MM:SS](https://www.youtube.com/watch?v=<Video ID>&t=<seconds>s)** - <Bullet 2: Specific, actionable detail>
    ... (Provide between 2 and 5 bullet points. Use fewer for short/simple videos, and more for dense/complex technical content.)

    **IMPORTANT TIMESTAMP FORMATTING:**
    - Each bullet point MUST start with a timestamp in the format [MM:SS] that links to that moment in the video.
    - Convert the timestamp seconds from the transcript to MM:SS format (e.g., 125 seconds becomes 02:05).
    - The timestamp should link to: https://www.youtube.com/watch?v=<Video ID>&t=<seconds>s
    - Choose the timestamp that best represents when that specific takeaway is discussed in the video.
    - Make the timestamp bold and followed by " - " before the bullet text.

    **(IMPORTANT: You must leave a blank line between 'Key Takeaways:' and the first bullet point so the list renders correctly.)**

    Data:
    {context_block}
    """

    logging.info(f"Sending request to OpenAI ({model})...")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        )
        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("OpenAI returned empty content")
        return content
    except Exception as e:
        logging.error(f"OpenAI API call failed: {e}")
        raise RuntimeError("OpenAI API call failed")


def generate_rss_feed(summaries: list[dict], output_file: str = "feed.xml"):
    """
    Generates an RSS feed from video summaries and writes it to a file.

    Args:
        summaries (list[dict]): List of dictionaries containing:
            - title (str): Video title
            - video_id (str): YouTube video ID
            - summary (str): Markdown summary of the video
            - timestamp (str): RFC 2822 formatted timestamp (e.g., "Mon, 01 Jan 2024 12:00:00 GMT")
        output_file (str): Path to output RSS file (default: "feed.xml")

    The function overwrites the output file on each execution.
    """
    # Create the root RSS element
    rss = Element("rss", version="2.0")
    rss.set("{http://www.w3.org/2005/Atom}atom", "http://www.w3.org/2005/Atom")
    channel = SubElement(rss, "channel")

    # Add channel metadata
    SubElement(channel, "title").text = "YouTube Digest Feed"
    SubElement(channel, "link").text = "https://github.com/greenbrettmichael/yt-digest"
    SubElement(channel, "description").text = "AI-powered summaries of YouTube videos"
    SubElement(channel, "language").text = "en-us"

    # Add atom:link for self-reference
    SubElement(
        channel,
        "{http://www.w3.org/2005/Atom}link",
        href=output_file,
        rel="self",
        type="application/rss+xml"
    )

    # Add each summary as an RSS item
    for entry in summaries:
        item = SubElement(channel, "item")

        SubElement(item, "title").text = entry["title"]
        SubElement(item, "link").text = f"https://www.youtube.com/watch?v={entry['video_id']}"
        SubElement(item, "guid", isPermaLink="false").text = entry["video_id"]
        SubElement(item, "pubDate").text = entry["timestamp"]

        # Truncate summary if too long (protect against excessive size)
        summary = entry["summary"]
        max_summary_length = 10000
        if len(summary) > max_summary_length:
            summary = summary[:max_summary_length] + "\n\n[Summary truncated due to length]"

        # Convert Markdown to HTML for proper rendering in RSS readers
        html_content = markdown.markdown(summary, extensions=["nl2br"])

        # Add description with proper CDATA handling
        description = SubElement(item, "description")
        description.text = html_content

    # Write to file (overwrite existing)
    try:
        # Format the XML with proper indentation
        xml_str = _prettify_xml(rss)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(xml_str)

        logging.info(f"Successfully wrote RSS feed with {len(summaries)} entries to {output_file}")
    except OSError as e:
        logging.error(f"Failed to write RSS feed to {output_file}: {type(e).__name__}: {e}")
        raise


def _prettify_xml(elem: Element, level: int = 0) -> str:
    """
    Returns a pretty-printed XML string for the Element.

    Args:
        elem: XML Element to prettify
        level: Current indentation level

    Returns:
        str: Formatted XML string
    """
    from xml.etree.ElementTree import tostring

    indent = "  "
    i = "\n" + level * indent
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + indent
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        last_child = None
        for child in elem:
            _prettify_xml(child, level + 1)
            last_child = child
        if last_child is not None and (not last_child.tail or not last_child.tail.strip()):
            last_child.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

    # Convert to string
    return tostring(elem, encoding="unicode")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv()

    # Try to load configuration from queries.json
    config_file = "queries.json"
    config_entries = []

    try:
        config_entries = load_queries_config(config_file)
        logging.info(f"Using configuration from {config_file}")
        if not config_entries:
            logging.error(f"No valid configuration entries found in {config_file}")
            exit(1)
    except Exception as e:
        logging.error(f"Failed to load configuration: {e}")
        exit(1)

    # Collect all summaries for RSS feed
    all_summaries = []

    # Process each configuration entry
    for idx, entry in enumerate(config_entries):
        search_url = entry.get("search_url")
        channel_id = entry.get("channel_id")
        channel_url = entry.get("channel_url")
        channel_username = entry.get("channel_username")

        logging.info(f"\n{'=' * 60}")
        logging.info(f"Processing entry {idx + 1}/{len(config_entries)}")
        if search_url:
            logging.info(f"Search URL: {search_url}")
        if channel_id:
            logging.info(f"Channel ID: {channel_id}")
        if channel_url:
            logging.info(f"Channel URL: {channel_url}")
        if channel_username:
            logging.info(f"Channel Username: {channel_username}")
        logging.info(f"{'=' * 60}\n")

        try:
            # Fetch transcripts from channels (if specified)
            data = []
            if channel_id or channel_url or channel_username:
                channel_data = get_channel_videos_last_day(
                    channel_id=channel_id, channel_url=channel_url, channel_username=channel_username
                )
                data.extend(channel_data)

            # Also fetch from search URL if specified
            if search_url:
                search_data = get_recent_transcripts(search_url, limit=2)
                data.extend(search_data)

            if not data:
                logging.warning(f"No transcripts found for entry {idx + 1}, skipping...")
                continue

            # Generate newsletter digest for each video individually to ensure one entry per video
            for video in data:
                # Generate summary for single video
                single_video_data = [video]
                try:
                    summary = generate_newsletter_digest(single_video_data)

                    summary_entry = {
                        "title": video["title"],
                        "video_id": video["video_id"],
                        "summary": summary,
                        "timestamp": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
                    }
                    all_summaries.append(summary_entry)
                    logging.info(f"Generated summary for: {video['title']}")
                except Exception as e:
                    logging.error(f"Error generating summary for {video['title']}: {e}")
                    continue

            logging.info(f"Successfully processed entry {idx + 1}\n")

        except Exception as e:
            logging.error(f"Error processing entry {idx + 1}: {e}")
            logging.info("Continuing with next entry...\n")
            continue

    # Generate RSS feed with all summaries
    if all_summaries:
        generate_rss_feed(all_summaries, output_file="feed.xml")
        logging.info(f"\nRSS feed generation complete! Total entries: {len(all_summaries)}")
    else:
        logging.warning("No summaries generated. RSS feed not created.")
