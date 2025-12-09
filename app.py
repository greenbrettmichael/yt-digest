import json
import logging
import os
import textwrap
from urllib.parse import parse_qs, urlparse

import markdown
import resend
import scrapetube
from dotenv import load_dotenv
from openai import OpenAI
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig


def decode_sp_parameter(sp_param: str) -> str | None:
    """
    Decode the YouTube sp parameter to extract the sort_by filter.

    The sp parameter follows the pattern: CA{sort_by_code}SAhA{results_type_code}
    This function extracts the sort_by_code and maps it back to the sort_by value.

    Args:
        sp_param (str): The sp parameter from YouTube URL (e.g., "CAASBAgCEAE=")

    Returns:
        str | None: The decoded sort_by value ("relevance", "upload_date", "view_count", or "rating"),
                    or None if decoding fails

    Examples:
        >>> decode_sp_parameter("CAASBAgCEAE=")
        'relevance'

        >>> decode_sp_parameter("CAISAhAB")
        'upload_date'
    """
    # Mapping from scrapetube's sort_by codes to sort_by values
    sort_by_reverse_map = {
        "A": "relevance",
        "I": "upload_date",
        "M": "view_count",
        "E": "rating",
    }

    try:
        # The sp parameter pattern is: CA{sort_by_code}SAhA{results_type_code}
        # Extract the character after "CA" which is the sort_by code
        if sp_param.startswith("CA") and len(sp_param) > 2:
            sort_by_code = sp_param[2]
            sort_by = sort_by_reverse_map.get(sort_by_code)
            if sort_by:
                logging.info(f"Decoded sp parameter: sort_by='{sort_by}' from code '{sort_by_code}'")
                return sort_by
            else:
                logging.warning(f"Unknown sort_by code '{sort_by_code}' in sp parameter")
                return None
        else:
            logging.warning(f"sp parameter '{sp_param}' does not follow expected pattern")
            return None
    except Exception as e:
        logging.warning(f"Failed to decode sp parameter '{sp_param}': {e}")
        return None


def parse_youtube_search_input(search_input: str) -> tuple[str, str | None]:
    """
    Parse a YouTube search input and extract the search query and optional sp parameter.

    This function accepts either:
    1. A plain keyword/search term (e.g., "python tutorials")
    2. A full YouTube search URL (e.g., "https://www.youtube.com/results?search_query=news&sp=...")

    When a URL is provided, it extracts:
    - search_query: The search term from the URL query parameter
    - sp: The advanced search filter parameter (if present)

    The sp parameter is decoded to extract the sort_by filter, which is then passed to scrapetube.

    Args:
        search_input (str): Either a plain keyword or a full YouTube search URL

    Returns:
        tuple[str, str | None]: A tuple containing (search_query, sort_by)
            - search_query: The extracted search term or the original input if not a URL
            - sort_by: The decoded sort_by value from sp parameter, or None if not present/decodable

    Examples:
        >>> parse_youtube_search_input("news")
        ('news', None)

        >>> parse_youtube_search_input("https://www.youtube.com/results?search_query=news")
        ('news', None)

        >>> parse_youtube_search_input("https://www.youtube.com/results?search_query=news&sp=CAASBAgCEAE%3D")
        ('news', 'relevance')
    """
    # Check if the input looks like a URL (contains :// or starts with www.)
    if "://" in search_input or search_input.startswith("www."):
        try:
            # Parse the URL to extract query parameters
            parsed_url = urlparse(search_input)
            query_params = parse_qs(parsed_url.query)

            # Extract search_query parameter (returns a list, take first element)
            search_query = query_params.get("search_query", [search_input])[0]

            # Extract sp parameter if present (returns a list, take first element)
            sp_param = query_params.get("sp", [None])[0]

            # Decode sp parameter to get sort_by value
            sort_by = None
            if sp_param:
                sort_by = decode_sp_parameter(sp_param)
                logging.info(f"Parsed URL - search_query: '{search_query}', sp: '{sp_param}', sort_by: '{sort_by}'")
            else:
                logging.info(f"Parsed URL - search_query: '{search_query}', no sp parameter")

            return search_query, sort_by

        except Exception as e:
            # If URL parsing fails, treat it as a plain keyword
            logging.warning(f"Failed to parse URL '{search_input}': {e}. Treating as plain keyword.")
            return search_input, None
    else:
        # Input is a plain keyword, not a URL
        return search_input, None


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


def get_recent_transcripts(keyword: str, limit: int = 10, api_client: YouTubeTranscriptApi | None = None) -> list[dict]:
    """
    Searches for the most recent videos by keyword or URL and retrieves their transcripts.

    This function accepts either a plain search keyword or a full YouTube search URL.
    When a URL is provided, it extracts the search_query and sp parameters automatically.
    The sp parameter is decoded to determine the sort_by filter.

    Args:
        keyword (str): Either a search keyword (e.g., "news") or a full YouTube search URL
                      (e.g., "https://www.youtube.com/results?search_query=news&sp=...")
        limit (int): The maximum number of videos to process.
        api_client (YouTubeTranscriptApi, optional): An instance of YouTubeTranscriptApi. If None, a new instance will be created.
    Returns:
        List of dictionaries containing video_id, title, and transcript for each video with available transcripts.
    """
    # Parse the input to extract search query and sort_by from sp parameter
    search_query, sort_by = parse_youtube_search_input(keyword)

    # Default to "relevance" if no sort_by was extracted
    if not sort_by:
        sort_by = "relevance"

    logging.info(f"Searching for most recent videos for keyword: '{search_query}' with sort_by: '{sort_by}'...")

    search_results = scrapetube.get_search(query=search_query, limit=limit, sort_by=sort_by, results_type="video")

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
    # Example usage TODO: make a proper entry point later
    KEYWORD = "News"
    logging.basicConfig(level=logging.INFO)

    data = get_recent_transcripts(KEYWORD, limit=2)

    output_filename = "transcripts.json"

    # 3. Save to Disk
    save_results_to_json(data, output_filename)

    newsletter = generate_newsletter_digest(data)

    # Save Newsletter to Markdown file
    md_filename = "digest.md"
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(newsletter)

    recipient = os.getenv("RECIPIENT_EMAIL")
    if recipient and os.getenv("RESEND_API_KEY"):
        send_newsletter_resend(subject="YT DIGEST", body=newsletter, recipients=[recipient])
