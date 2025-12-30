# Development Guide

This document provides guidance for developers who want to contribute to or modify the `yt-digest` project.

## Prerequisites for Development

- **Python 3.10**: This project requires Python 3.10 or higher
- **Conda**: For managing the Python environment ([Installation Guide](https://docs.conda.io/projects/conda/en/latest/user-guide/install/))
- Familiarity with Python development practices

## Setting Up the Development Environment

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

## Code Quality Tools

This project uses multiple tools to maintain code quality and consistency.

### Ruff

[Ruff](https://docs.astral.sh/ruff/) is used for linting and code formatting.

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

### Flake8

[Flake8](https://flake8.pycqa.org/) is used for additional style checking.

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

### mypy

[mypy](http://mypy-lang.org/) is used for static type checking.

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
- Third-party libraries without type stubs (scrapetube) are configured to ignore missing imports

## Testing

Run tests using pytest:

```bash
pytest -v
```

All tests should pass before submitting any changes.

## Code Style Guidelines

- Follow PEP 8 style guidelines (enforced by Ruff and Flake8)
- Use type hints where appropriate
- Keep line length under 120 characters
- Write clear, descriptive docstrings for all public functions
- Ensure all tests pass before committing changes

## Submitting Changes

1. Create a new branch for your changes
2. Make your changes and test thoroughly
3. Run all linting and testing tools to ensure code quality
4. Commit your changes with clear, descriptive commit messages
5. Submit a pull request with a detailed description of your changes
