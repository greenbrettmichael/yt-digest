# Advanced Usage Guide

This document provides advanced usage examples and customization options for `yt-digest`.

## Customizing the Script

You can modify the behavior of `yt-digest` by editing `app.py` directly or by using the provided functions in your own Python scripts.

### Customization Options

```python
# Adjust number of videos to process per search query (default: 2)
data = get_recent_transcripts(search_url, limit=5)

# Customize OpenAI model (default: "gpt-5-mini-2025-08-07")
newsletter = generate_newsletter_digest(data, model="gpt-4-turbo-preview")

# Customize RSS feed output file name (default: "feed.xml")
generate_rss_feed(all_summaries, output_file="my_custom_feed.xml")
```

## Advanced Workflows

### Workflow 1: Generate summaries and RSS feed

This workflow demonstrates how to search for videos, generate summaries, and create an RSS feed programmatically:

```python
import logging
from app import get_recent_transcripts, generate_newsletter_digest, generate_rss_feed
from datetime import datetime

logging.basicConfig(level=logging.INFO)

# Search and extract transcripts using a full YouTube URL
url = "https://www.youtube.com/results?search_query=Python+tutorials&sp=EgIIAw%253D%253D"
data = get_recent_transcripts(url, limit=3)

# Generate summaries for each video
all_summaries = []
for video in data:
    summary = generate_newsletter_digest([video])
    all_summaries.append({
        "title": video["title"],
        "video_id": video["video_id"],
        "summary": summary,
        "timestamp": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    })

# Generate RSS feed
generate_rss_feed(all_summaries, output_file="feed.xml")
```

### Workflow 2: Generate digest without RSS feed

This workflow shows how to extract transcripts and generate summaries without creating an RSS feed:

```python
from app import get_recent_transcripts, save_results_to_json, generate_newsletter_digest

# Search and extract transcripts
url = "https://www.youtube.com/results?search_query=Python+tutorials&sp=EgIIAw%253D%253D"
data = get_recent_transcripts(url, limit=3)

# Save raw data
save_results_to_json(data, "python_transcripts.json")

# Generate digest
newsletter = generate_newsletter_digest(data)

# Save to file
with open("python_digest.md", "w") as f:
    f.write(newsletter)
```

## Function Documentation

### Getting Help

For more details on individual functions and their parameters, refer to their docstrings:

```bash
python -c "from app import get_recent_transcripts; help(get_recent_transcripts)"
```

### Core Functions

The main functions available for programmatic use include:

- `get_transcript_api()`: Initialize the YouTube Transcript API with proxy configuration
- `load_queries_config(config_path)`: Load and validate queries from a JSON file
- `get_recent_transcripts(search_url, limit)`: Search and extract video transcripts
- `generate_newsletter_digest(data, model)`: Generate AI-powered summaries
- `generate_rss_feed(summaries, output_file)`: Create an RSS feed from summaries
- `save_results_to_json(data, filename)`: Save transcript data to a JSON file

## Custom Integration Examples

### Integration with Other Tools

You can integrate `yt-digest` with other tools and services:

**Example: Email notifications**
```python
import smtplib
from email.mime.text import MIMEText
from app import get_recent_transcripts, generate_newsletter_digest

# Generate digest
url = "https://www.youtube.com/results?search_query=tech+news&sp=EgIIAw%253D%253D"
data = get_recent_transcripts(url, limit=3)
digest = generate_newsletter_digest(data)

# Send via email
msg = MIMEText(digest)
msg['Subject'] = 'Daily YouTube Digest'
msg['From'] = 'sender@example.com'
msg['To'] = 'recipient@example.com'

# Configure your SMTP server
s = smtplib.SMTP('localhost')
s.send_message(msg)
s.quit()
```

**Example: Slack notifications**
```python
import requests
from app import get_recent_transcripts, generate_newsletter_digest

# Generate digest
url = "https://www.youtube.com/results?search_query=tech+news&sp=EgIIAw%253D%253D"
data = get_recent_transcripts(url, limit=3)
digest = generate_newsletter_digest(data)

# Send to Slack
webhook_url = 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
requests.post(webhook_url, json={'text': digest})
```

## Performance Considerations

- **Transcript Length**: Transcripts are automatically truncated to 15,000 characters to manage API costs and processing time
- **Summary Length**: RSS feed summaries are truncated to 10,000 characters to prevent excessive feed sizes
- **API Rate Limits**: Be mindful of OpenAI API rate limits when processing large numbers of videos
- **Video Limit**: By default, only 2 videos are processed per query. Adjust the `limit` parameter based on your needs and API constraints

## Troubleshooting

### Common Issues

**Issue: API rate limits**
- Solution: Reduce the number of videos processed per query or implement exponential backoff

**Issue: Large transcript processing**
- Solution: Transcripts are automatically truncated, but you can adjust the limit in the code if needed

**Issue: Memory usage**
- Solution: Process videos in smaller batches if working with many queries

For additional help, refer to the main [README](README.md) or the [Development Guide](DEVELOPMENT.md).
