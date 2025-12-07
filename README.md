# yt-digest

A YouTube transcript digest generator that searches for YouTube videos, extracts transcripts, and generates AI-powered newsletter digests using OpenAI's GPT models. The tool can automatically send formatted newsletters via email.

## Local Setup

### Prerequisites

Before setting up the project, ensure you have the following installed:

- **Python 3.10**: This project requires Python 3.10 or higher
- **Conda**: For managing the Python environment ([Installation Guide](https://docs.conda.io/projects/conda/en/latest/user-guide/install/))
- **API Keys**: You'll need API keys for the following services:
  - [OpenAI API Key](https://platform.openai.com/api-keys) - For generating newsletter digests
  - [Webshare Proxy](https://www.webshare.io/) credentials - For accessing YouTube transcripts (username and password)
  - [Resend API Key](https://resend.com/api-keys) - For sending email newsletters (optional)

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
   - `resend` - For sending email newsletters
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
   
   # Resend Configuration (optional, for email newsletters)
   RESEND_API_KEY=re_your-resend-api-key
   # Use 'onboarding@resend.dev' to test without a custom domain
   RESEND_FROM_EMAIL=onboarding@resend.dev
   
   # Newsletter Recipient
   RECIPIENT_EMAIL=your-email@example.com
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

**Issue: Email sending fails**
- Ensure RESEND_API_KEY is set correctly
- When testing, use `onboarding@resend.dev` as the FROM_EMAIL
- Check that the recipient email is valid

## Basic Usage

### Running the Main Script

The project can be run directly using the main script:

```bash
python app.py
```

By default, this will:
1. Search for recent videos matching the keyword "News" (configurable in the script)
2. Fetch transcripts for up to 2 videos
3. Save raw transcripts to `transcripts.json`
4. Generate an AI newsletter digest and save it to `digest.md`
5. Send the newsletter via email (if email credentials are configured)

### Core Functionality

The `yt-digest` tool provides several key functions:

1. **Video Search and Transcript Extraction**:
   - Searches YouTube for videos by keyword
   - Retrieves English transcripts (or falls back to other available languages)
   - Handles videos with disabled or missing transcripts gracefully

2. **AI-Powered Digest Generation**:
   - Uses OpenAI's GPT models to analyze transcripts
   - Generates concise, structured newsletter format
   - Includes video titles, links, and key takeaways

3. **Email Newsletter Distribution**:
   - Converts Markdown to HTML email format
   - Sends newsletters via Resend API
   - Supports plain text fallback

### Customizing the Script

You can modify the behavior by editing `app.py`:

```python
# Change search keyword
KEYWORD = "AI News"  # Default: "News"

# Adjust number of videos to process
data = get_recent_transcripts(KEYWORD, limit=5)  # Default: 2

# Customize OpenAI model
newsletter = generate_newsletter_digest(data, model="gpt-4-turbo-preview")

# Change output filenames
output_filename = "my_transcripts.json"
md_filename = "my_digest.md"
```

### Example Usage Workflows

**Workflow 1: Generate a digest without sending email**
```python
import logging
from app import get_recent_transcripts, save_results_to_json, generate_newsletter_digest

logging.basicConfig(level=logging.INFO)

# Search and extract transcripts
data = get_recent_transcripts("Python tutorials", limit=3)

# Save raw data
save_results_to_json(data, "python_transcripts.json")

# Generate digest
newsletter = generate_newsletter_digest(data)

# Save to file
with open("python_digest.md", "w") as f:
    f.write(newsletter)
```

**Workflow 2: Send a custom newsletter**
```python
from app import send_newsletter_resend

subject = "Weekly Tech Digest"
body = "# Your newsletter content here\n\n- Item 1\n- Item 2"
recipients = ["subscriber1@example.com", "subscriber2@example.com"]

send_newsletter_resend(subject, body, recipients)
```

### Command-Line Help

For more details on individual functions, refer to their docstrings:

```bash
python -c "from app import get_recent_transcripts; help(get_recent_transcripts)"
```

## Development

### Code Quality

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and code formatting, and [mypy](http://mypy-lang.org/) for static type checking.

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
