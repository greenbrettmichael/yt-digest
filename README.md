# yt-digest

A YouTube transcript digest generator that searches for YouTube videos, extracts transcripts, and generates AI-powered summaries using OpenAI's GPT models. The tool outputs summaries to an RSS feed for easy consumption in your favorite RSS reader.

## Local Setup

### Prerequisites

Before setting up the project, ensure you have the following installed:

- **Python 3.10**: This project requires Python 3.10 or higher
- **Conda**: For managing the Python environment ([Installation Guide](https://docs.conda.io/projects/conda/en/latest/user-guide/install/))
- **API Keys**: You'll need API keys for the following services:
  - [OpenAI API Key](https://platform.openai.com/api-keys) - For generating video summaries
  - [Webshare Proxy](https://www.webshare.io/) credentials - For accessing YouTube transcripts (username and password)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/greenbrettmichael/yt-digest.git
   cd yt-digest
   ```

2. **Create and activate the Conda environment**:
   ```bash
   conda env create -f environment.yaml
   conda activate yt_digest
   ```

   This will install all required dependencies including:
   - `scrapetube` - For searching YouTube videos
   - `youtube-transcript-api` - For fetching video transcripts
   - `openai` - For generating AI-powered digests
   - `pytest` and `ruff` - For testing and linting

3. **Configure environment variables**:
   
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your credentials:
   ```bash
   # Proxy configuration for YouTube Transcript API
   PROXY_USERNAME=your_webshare_username
   PROXY_PASSWORD=your_webshare_password
   
   # OpenAI API Key
   OPENAI_API_KEY=sk-your-openai-api-key
   ```

### Troubleshooting

**Issue: Conda environment creation fails**
- Ensure you have Conda installed and updated: `conda update conda`
- Try creating the environment with: `conda env create -f environment.yaml --force`

**Issue: Proxy authentication errors**
- Verify your Webshare proxy credentials are correct
- Ensure your proxy subscription is active

**Issue: OpenAI API errors**
- Check that your API key is valid and has available credits
- Verify the model name in the code matches available models in your OpenAI account

## Basic Usage

### Configuration Using queries.json

Create a `queries.json` file in the project root directory with the following structure:

```json
[
    {
        "search_url": "https://www.youtube.com/results?search_query=python+tutorials&sp=EgIIAw%253D%253D"
    },
    {
        "channel_username": "LinusTechTips"
    },
    {
        "channel_id": "UC8butISFwT-Wl7EV0hUK0BQ"
    },
    {
        "channel_url": "https://www.youtube.com/@mkbhd"
    },
    {
        "channel_username": "ThePrimeagen",
        "search_url": "https://www.youtube.com/results?search_query=programming&sp=EgIIAw%253D%253D"
    }
]
```

**Configuration File Format:**
- The file must be a JSON array of objects
- Each object represents a video source query
- Required fields for each entry:
  - At least one video source (can have multiple):
    - `search_url`: Full YouTube search URL for keyword-based searches
    - `channel_id`: YouTube channel ID (e.g., "UC8butISFwT-Wl7EV0hUK0BQ")
    - `channel_url`: YouTube channel URL (e.g., "https://www.youtube.com/@mkbhd")
    - `channel_username`: YouTube channel username without @ (e.g., "LinusTechTips")

**Using Channel Sources:**
- When you specify a channel (via `channel_id`, `channel_url`, or `channel_username`), the tool will:
  - Query the channel for videos published in the last 24 hours
  - Process transcripts for all videos found
  - Include them in the RSS feed
- You can specify multiple sources per query (e.g., both a channel and a search URL)
- Channel videos are fetched using `scrapetube.get_channel()` sorted by newest first

**How to Construct YouTube Search URLs:**
1. Go to YouTube and perform your desired search
2. Apply any filters (upload date, duration, etc.)
3. Copy the complete URL from your browser's address bar
4. The URL should include the `sp` parameter for filters, e.g., `sp=EgIIAw%253D%253D` for videos uploaded this week

**Finding Channel Identifiers:**
- **Channel Username**: The handle shown on the channel page (without the @), e.g., "LinusTechTips"
- **Channel URL**: The full URL to the channel page, e.g., "https://www.youtube.com/@mkbhd"
- **Channel ID**: Found in the page source or channel URL, e.g., "UC8butISFwT-Wl7EV0hUK0BQ"

**Example:** A `queries.json.example` file is provided in the repository for reference.

### Running the Main Script

The project can be run directly using the main script:

```bash
python app.py
```

- The application processes each entry in the configuration file
- For each entry, it will:
  1. Fetch videos from the last 24 hours from any specified channels
  2. Fetch transcripts for videos matching any search URLs
  3. Generate an AI summary for each video individually
  4. Add each summary as a separate entry to the RSS feed
- The RSS feed is written to `feed.xml` in the project root
- Each execution overwrites the previous `feed.xml` with newly generated content
- If any entry fails, the application logs the error and continues with the next entry
- The tool logs the number of videos found and which channels were processed

### RSS Feed Output

The generated `feed.xml` file:
- Contains one RSS item per video summary
- Includes video title, YouTube link, publication date, and AI-generated summary
- Is compatible with standard RSS readers (Feedly, Inoreader, etc.)
- Summaries are truncated to 10,000 characters if too long to protect against excessive size
- The feed is completely regenerated on each run (previous entries are overwritten)

### Core Functionality

The `yt-digest` tool provides several key functions:

1. **Video Search and Transcript Extraction**:
   - Searches YouTube for videos by keyword
   - Retrieves English transcripts (or falls back to other available languages)
   - Handles videos with disabled or missing transcripts gracefully

2. **AI-Powered Digest Generation**:
   - Uses OpenAI's GPT models to analyze transcripts
   - Generates concise, structured summaries for each video
   - Includes video titles, links, and key takeaways with timestamps
   - Transcripts are truncated to 15,000 characters to handle large queries efficiently

3. **RSS Feed Generation**:
   - Outputs all summaries to a single `feed.xml` file
   - Each video gets its own RSS item entry
   - Compatible with all standard RSS readers
   - Summaries are truncated to 10,000 characters to prevent excessive size

### Customizing the Script

**For advanced users:** You can modify the behavior by editing `app.py`:

```python
# Adjust number of videos to process per search query (default: 2)
data = get_recent_transcripts(search_url, limit=5)

# Customize OpenAI model (default: "gpt-5-mini-2025-08-07")
newsletter = generate_newsletter_digest(data, model="gpt-4-turbo-preview")

# Customize RSS feed output file name (default: "feed.xml")
generate_rss_feed(all_summaries, output_file="my_custom_feed.xml")
```

### Example Usage Workflows

**Workflow 1: Generate summaries and RSS feed**
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

**Workflow 2: Generate digest without RSS feed**
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

### Command-Line Help

For more details on individual functions, refer to their docstrings:

```bash
python -c "from app import get_recent_transcripts; help(get_recent_transcripts)"
```

## Development

### Code Quality

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and code formatting, [Flake8](https://flake8.pycqa.org/) for additional style checking, and [mypy](http://mypy-lang.org/) for static type checking.

#### Running Ruff

To check your code for linting issues:

```bash
ruff check .
```

To automatically fix auto-fixable issues:

```bash
ruff check --fix .
```

To format your code:

```bash
ruff format .
```

#### Ruff Configuration

Ruff is configured via `pyproject.toml` in the project root. The configuration includes:
- Line length limit: 120 characters
- Python version target: 3.10
- Enabled rule sets: pycodestyle, pyflakes, isort, pep8-naming, pyupgrade, flake8-bugbear, flake8-comprehensions, and flake8-simplify

#### Running Flake8

To check your code for style and formatting issues:

```bash
flake8 .
```

#### Flake8 Configuration

Flake8 is configured via `.flake8` in the project root. The configuration includes:
- Line length limit: 120 characters
- Excludes: `.git`, `.pytest_cache`, `__pycache__`, and other build/environment directories
- Some rules are ignored to align with the project's code style (E501, E722, W503)

#### Running mypy

To check your code for type errors:

```bash
mypy app.py tests/
```

#### mypy Configuration

mypy is configured via `pyproject.toml` in the project root. The configuration includes:
- Python version target: 3.10
- Type checking for untyped code enabled
- No implicit optional types allowed
- Third-party libraries without type stubs (scrapetube, resend) are configured to ignore missing imports

### Testing

Run tests using pytest:

```bash
pytest -v
```
