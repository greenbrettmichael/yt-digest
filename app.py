import json
import logging
import os
import textwrap

import markdown
import resend
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


def load_email_list_config(config_path: str = "email_list.json") -> list[dict]:
    """
    Loads and validates the email list configuration from a JSON file.

    Args:
        config_path (str): Path to the email_list.json configuration file.

    Returns:
        list[dict]: A list of validated configuration entries, each containing:
            - email (str): Recipient email address
            - search_url (str): YouTube search URL

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

        email = entry.get("email")
        search_url = entry.get("search_url")

        if not email or not isinstance(email, str) or not email.strip():
            logging.warning(f"Entry at index {idx} missing or invalid 'email' field")
            continue

        if not search_url or not isinstance(search_url, str) or not search_url.strip():
            logging.warning(f"Entry at index {idx} missing or invalid 'search_url' field")
            continue

        # Basic email format validation
        if "@" not in email:
            logging.warning(f"Entry at index {idx} has invalid email format")
            continue
        validated_entries.append({"email": email.strip(), "search_url": search_url.strip()})

    if len(validated_entries) == 0:
        logging.warning("Configuration file contains no valid entries")
        return []

    logging.info(f"Successfully loaded {len(validated_entries)} configuration entries from {config_path}")
    return validated_entries


def get_recent_transcripts(url: str, limit: int = 10, api_client: YouTubeTranscriptApi | None = None) -> list[dict]:
    """
    Searches for the most recent videos by URL and retrieves their transcripts.

    Args:
        url (str):  A full YouTube search URL with optional sp parameter for advanced filtering
        limit (int): The maximum number of videos to process.
        api_client (YouTubeTranscriptApi, optional): An instance of YouTubeTranscriptApi. If None, a new instance will be created.
    Returns:
        List of dictionaries containing video_id, title, and transcript for each video with available transcripts.
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

        transcript_text = ""
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

            # Combine the text parts into a single string, discarding timestamps for now
            transcript_text = " ".join([item.text for item in fetched_transcript])

        except TranscriptsDisabled:
            logging.info(f"Transcripts are disabled for video ID: {video_id}")
            continue
        except NoTranscriptFound:
            logging.info(f"No transcript found for video ID: {video_id}.")
            continue
        except Exception as e:
            logging.info(f"Error retrieving transcript for video ID: {video_id}: {str(e)}")
            continue

        results_data.append({"video_id": video_id, "title": title, "transcript": transcript_text})

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
    Sends transcript data to OpenAI to generate a newsletter digest.

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

    # Pre-process the data
    # We construct a string where we label every transcript clearly.
    context_block = ""
    for i, item in enumerate(json_data, 1):
        # We include the ID so the LLM can generate YouTube links
        context_block += f"--- VIDEO {i} ---\n"
        context_block += f"Title: {item['title']}\n"
        context_block += f"Video ID: {item['video_id']}\n"
        # Truncate very long transcripts if necessary (e.g., to 25k chars) to fit context
        context_block += f"Transcript: {item['transcript'][:25000]}\n\n"

    # Define the System Prompt
    system_prompt = (
        "You are an expert tech newsletter editor. Your goal is to synthesize "
        "raw video transcripts into a concise, high-value weekly digest."
    )

    # Define the User Prompt
    user_prompt = f"""
    Here are the transcripts from the most recent videos.

    Please write a Newsletter Digest in Markdown format.

    **Strict Formatting Rules:**
    1. Do NOT include a main headline or title at the top.
    2. Do NOT include an Executive Summary or Intro.
    3. Start directly with the list of videos.
    4. Do NOT include a "TL;DR" line for the videos.
    5. Do NOT include any concluding remarks, "If you want...", or offers for further instructions at the end.

    **Structure for each video:**
    ### Title: <Original Video Title>
    Link: [Watch on YouTube](https://www.youtube.com/watch?v=<Video ID>)
    Key Takeaways:

    - <Bullet 1: Specific, actionable detail>
    - <Bullet 2: Specific, actionable detail>
    ... (Provide between 2 and 5 bullet points. Use fewer for short/simple videos, and more for dense/complex technical content.)

    **(IMPORTANT: You must leave a blank line between 'Key Takeaways:' and the first bullet point so the list renders correctly.)**
    ---

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


def markdown_to_email_html(md_content: str) -> str:
    """
    Converts Markdown to HTML with basic email styling.

    Args:
        md_content (str): The raw Markdown content.
    Returns:
        str: The HTML content suitable for email bodies.
    """
    html_content = markdown.markdown(md_content, extensions=["nl2br"])

    return textwrap.dedent(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h3 {{ color: #1a1a1a; margin-top: 20px; margin-bottom: 5px; }}
                a {{ color: #0066cc; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                /* Ensure lists render cleanly */
                ul {{ margin-top: 0; padding-left: 20px; margin-bottom: 20px; }}
                li {{ margin-bottom: 5px; }}
                hr {{ border: 0; border-top: 1px solid #eeeeee; margin: 20px 0; }}
                .footer {{ font-size: 12px; color: #888888; margin-top: 30px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                {html_content}
                <div class="footer">
                    <p>Generated by AI • Powered by Python</p>
                </div>
            </div>
        </body>
        </html>
    """).strip()


def send_newsletter_resend(subject: str, body: str, recipients: list):
    """
    Sends the newsletter using the Resend API.

    Args:
        subject (str): The email subject line.
        body (str): The email body content.
        recipients (list): A list of email addresses to send to.
    Raises:
        RuntimeError: If sending the email fails.
    """
    api_key = os.getenv("RESEND_API_KEY")
    # Resend requires a verified domain, or you can test using 'onboarding@resend.dev'
    # to send ONLY to your own email address.
    from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")

    if not api_key:
        logging.warning("Skipping email: RESEND_API_KEY not set.")
        return

    if not recipients:
        logging.warning("Skipping email: No recipients provided.")
        return

    resend.api_key = api_key
    html_body = markdown_to_email_html(body)

    try:
        logging.info(f"Sending email via Resend to {len(recipients)} recipient(s)...")

        params = {
            "from": from_email,
            "to": recipients,
            "subject": subject,
            "text": body,  # Plain text fallback for email clients that don't support HTML
            "html": html_body,  # HTML version with styling for modern email clients
        }

        # Resend library lacks complete type annotations for SendParams
        email = resend.Emails.send(params)  # type: ignore[arg-type]

        # Resend returns an object (or dict) containing the ID
        if email and "id" in email:
            logging.info(f"Email sent successfully! ID: {email['id']}")
        else:
            logging.error(f"Resend did not return an ID. Response: {email}")
            raise RuntimeError(f"Resend did not return an ID. Response: {email}")
    except Exception as e:
        logging.error(f"Failed to send email via Resend: {e}")
        raise RuntimeError(f"Resend Error: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv()

    # Try to load configuration from email_list.json
    config_file = "email_list.json"
    config_entries = []

    try:
        config_entries = load_email_list_config(config_file)
        logging.info(f"Using configuration from {config_file}")
        if not config_entries:
            logging.error(f"No valid configuration entries found in {config_file}")
            exit(1)

    # Process each configuration entry
    for idx, entry in enumerate(config_entries):
        recipient_email = entry["email"]
        search_url = entry["search_url"]

        logging.info(f"\n{'=' * 60}")
        logging.info(f"Processing entry {idx + 1}/{len(config_entries)}")
        logging.info(f"Recipient: {recipient_email}")
        logging.info(f"Search URL: {search_url}")
        logging.info(f"{'=' * 60}\n")

        try:
            # Fetch transcripts
            data = get_recent_transcripts(search_url, limit=2)

            if not data:
                logging.warning(f"No transcripts found for {recipient_email}, skipping...")
                continue

            # Generate newsletter digest
            newsletter = generate_newsletter_digest(data)

            # Send email
            send_newsletter_resend(subject="YT DIGEST", body=newsletter, recipients=[recipient_email])

            logging.info(f"Successfully processed entry for {recipient_email}\n")

        except Exception as e:
            logging.error(f"Error processing entry for {recipient_email}: {e}")
            logging.info("Continuing with next entry...\n")
            continue
