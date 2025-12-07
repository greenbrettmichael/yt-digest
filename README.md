# yt-digest

A YouTube transcript digest generator.

## Development

### Setup

This project uses Conda for environment management. To set up the development environment:

```bash
conda env create -f environment.yaml
conda activate yt_digest
```

### Code Quality

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and code formatting.

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

### Testing

Run tests using pytest:

```bash
pytest -v
```
