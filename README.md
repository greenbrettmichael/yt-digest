# yt-digest

A YouTube transcript digest generator that searches for YouTube videos, extracts transcripts, and generates AI-powered summaries using OpenAI's GPT models. The tool outputs summaries to an RSS feed for easy consumption in your favorite RSS reader.

> **Maintenance Mode**: This project has reached maturity and is now in maintenance mode. It is stable and feature-complete for its intended use case. While critical bug fixes and security updates will be addressed, no major new features are planned. The project remains actively maintained and ready for use.

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

**Conda environment creation fails**
- Ensure Conda is installed and updated: `conda update conda`
- Try creating the environment with: `conda env create -f environment.yaml --force`

**Proxy authentication errors**
- Verify your Webshare proxy credentials are correct in `.env`
- Ensure your proxy subscription is active

**OpenAI API errors**
- Check that your API key is valid and has available credits
- Verify the model name in the code matches available models in your OpenAI account

For more detailed troubleshooting and advanced configuration, see the [Advanced Usage Guide](ADVANCED_USAGE.md).

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

## Additional Documentation

- **[Advanced Usage Guide](ADVANCED_USAGE.md)** - Customization options, advanced workflows, and programmatic usage examples
- **[Development Guide](DEVELOPMENT.md)** - Setup instructions, code quality tools, and contribution guidelines
- **[Deployment Guide](DEPLOYMENT.md)** - AWS Fargate deployment instructions for production use

## Contributing

This project is in maintenance mode but we still welcome contributions for bug fixes and security updates. Please see the [Development Guide](DEVELOPMENT.md) for information on setting up your development environment and code quality standards.

## License

This project is open source. Please refer to the repository for license information.
