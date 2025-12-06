import os
import scrapetube
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.proxies import WebshareProxyConfig
import logging
from dotenv import load_dotenv

def get_transcript_api():
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

def get_recent_transcripts(keyword: str, limit: int = 10):
    """
    Searches for the most recent videos by keyword and retrieves their transcripts.

    Args:
        keyword (str): The search keyword.
        limit (int): The maximum number of videos to process.
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
    transcript_api = get_transcript_api()

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

if __name__ == "__main__":
    # Example usage TODO: make a proper entry point later
    KEYWORD = "News"
    logging.basicConfig(level=logging.INFO)
    
    data = get_recent_transcripts(KEYWORD, limit=1)

    print("\n--- Summary ---")
    for item in data:
        print(f"Video: {item['title']}")
        print(f"Snippet: {item['transcript'][:100]}...") # Print first 100 chars
        print("-" * 30)