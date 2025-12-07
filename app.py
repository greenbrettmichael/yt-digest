import json
import os
from typing import Dict, List
import scrapetube
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.proxies import WebshareProxyConfig
import logging
from dotenv import load_dotenv
from openai import OpenAI

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

def get_recent_transcripts(keyword: str, limit: int = 10, api_client: YouTubeTranscriptApi = None) -> List[Dict]:
    """
    Searches for the most recent videos by keyword and retrieves their transcripts.

    Args:
        keyword (str): The search keyword.
        limit (int): The maximum number of videos to process.
        api_client (YouTubeTranscriptApi, optional): An instance of YouTubeTranscriptApi. If None, a new instance will be created.
    Returns:
        List of dictionaries containing video_id, title, and transcript for each video with available transcripts.
    """
    logging.info(f"Searching for most recent videos for keyword: '{keyword}'...")

    search_results = scrapetube.get_search(
        query=keyword,
        limit=limit,
        sort_by="relevance",
        results_type="video"
    )

    videos_processed = 0
    results_data = []
    transcript_api = api_client or get_transcript_api()

    for video in search_results:
        video_id = video.get('videoId')
        try:
            title = video['title']['runs'][0]['text']
        except (KeyError, IndexError):
            title = "Unknown Title"

        logging.info(f"Processing ({videos_processed + 1}/{limit}): {title} [{video_id}]")
        videos_processed += 1

        transcript_text = ""
        try:
            transcript_list_obj = transcript_api.list(video_id)
            
            # Try to find English variants first
            try:
                transcript_obj = transcript_list_obj.find_transcript(['en', 'en-US', 'en-GB'])
                logging.info(f"Found English transcript for video ID: {video_id} with language code: {transcript_obj.language_code}")
            except:
                # Fallback: If no English, just take the first available one (e.g., Spanish, Auto-generated, etc.)
                transcript_obj = next(iter(transcript_list_obj))
                logging.info(f"No English transcript found. Using available transcript with language code: {transcript_obj.language_code} for video ID: {video_id}")

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

        results_data.append({
            'video_id': video_id,
            'title': title,
            'transcript': transcript_text
        })
        

    return results_data

def save_results_to_json(results: List[Dict], filename: str):
    """
    Saves the list of transcript dictionaries to a JSON file.
    
    Args:
        results (List[Dict]): The list of dictionaries from get_recent_transcripts.
        filename (str): The output filename.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # indent=4 makes it pretty. ensure_ascii=False keeps emojis/foreign chars readable.
            json.dump(results, f, indent=4, ensure_ascii=False)
        logging.info(f"Successfully saved {len(results)} records to {filename}")
    except IOError as e:
        logging.error(f"Failed to write to file {filename}: {type(e).__name__}: {e}")
        raise

def generate_newsletter_digest(json_data: List[Dict], model: str = "gpt-5-mini-2025-08-07") -> str:
    """
    Sends transcript data to OpenAI to generate a newsletter digest.

    Args:
        json_data (List[Dict]): The list of video dictionaries.
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
    Link: https://www.youtube.com/watch?v=<Video ID>
    Key Takeaways:
    - <Bullet 1: Specific, actionable detail>
    - <Bullet 2: Specific, actionable detail>
    ... (Provide between 2 and 5 bullet points. Use fewer for short/simple videos, and more for dense/complex technical content.)
    
    ---
    
    Data:
    {context_block}
    """

    logging.info(f"Sending request to OpenAI ({model})...")
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"OpenAI API call failed: {e}")
        raise RuntimeError(f"OpenAI API call failed")

if __name__ == "__main__":
    # Example usage TODO: make a proper entry point later
    KEYWORD = "News"
    logging.basicConfig(level=logging.INFO)
    
    data = get_recent_transcripts(KEYWORD, limit=10)

    output_filename = "transcripts.json"

    # 3. Save to Disk
    save_results_to_json(data, output_filename)

    newsletter = generate_newsletter_digest(data)
        
    # Save Newsletter to Markdown file
    md_filename = f"digest.md"
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(newsletter)