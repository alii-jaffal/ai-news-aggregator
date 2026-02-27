 # AI News Aggregator

AI News Aggregator is an end-to-end pipeline that collects AI-related updates from multiple sources, stores them in PostgreSQL, enriches the content (transcripts/markdown), generates structured digests using an LLM, ranks them for a user profile, and sends a daily email newsletter (plain text + HTML).

The project is modular by design: scrapers, database/repository layer, processing services, LLM agents, and a single orchestrator that runs the full pipeline.

## What it does

High-level flow:

1. Scrape new items and store raw records in PostgreSQL
2. Fill missing Anthropic markdown (webpage → markdown)
3. Fill missing YouTube transcripts (when available)
4. Generate digests for items that do not yet have one
5. Rank recent digests for the user profile
6. Generate and send the email digest

## Features

- Multi-source ingestion
  - YouTube uploads via RSS
  - OpenAI news/blog via RSS
  - Anthropic feeds (RSS sources configured in the scraper)
- PostgreSQL persistence (Docker)
- Content enrichment
  - YouTube transcripts (youtube-transcript-api)
  - Anthropic markdown extraction (Docling)
- Digest generation (LLM)
  - Structured output (title + summary) validated with Pydantic
- Ranking (LLM curator)
  - Personalized scoring (0–10) and ordered ranking for a user profile
- Email delivery
  - LLM-generated introduction
  - Markdown rendering to styled HTML
  - Gmail SMTP delivery using an app password

## Project structure

```text
app/
  agent/
    curator_agent.py
    digest_agent.py
    email_agent.py
  database/
    connection.py
    create_tables.py
    models.py
    repository.py
  profiles/
    user_profile.py
  scrapers/
    anthropic.py
    openai.py
    youtube.py
  services/
    email_service.py
    process_anthropic.py
    process_digest.py
    process_email.py
    process_youtube.py
  config.py
  pipeline.py
  runner.py

docker/
  docker-compose.yml
```

## Tech stack

- Python 3.11+
- PostgreSQL (Docker)
- SQLAlchemy + Repository pattern
- Pydantic
- Google Gemini (structured outputs)
- Docling (webpage → markdown)
- feedparser (RSS)
- markdown (Markdown → HTML)
- SMTP (Gmail)

## Setup

### 1) Start PostgreSQL (Docker)

From the `docker/` directory:

```bash
docker compose up -d
```

Verify:

```bash
docker ps
```

### 2) Install dependencies

If you use `uv`:

```bash
uv sync
```

### 3) Environment variables

Create a `.env` file for the Python app (recommended location: repository root):

```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_news_aggregator

# Gemini API keys
DIGEST_GEMINI_API_KEY=...
CURATOR_GEMINI_API_KEY=...
EMAIL_GEMINI_API_KEY=...

# Email (Gmail SMTP)
MY_EMAIL=your_email@gmail.com
APP_PASSWORD=your_gmail_app_password

# Optional proxy (used by youtube-transcript-api if configured)
PROXY_USERNAME=
PROXY_PASSWORD=
```

Security notes:
- Do not commit `.env`. Add it to `.gitignore`.
- For Gmail, use an app password (requires 2FA) instead of your normal account password.

### 4) Create database tables

```bash
uv run -m app.database.create_tables
```

## Usage

### Scrape only

```bash
uv run -m app.runner
```

### Run the full pipeline

```bash
uv run -m app.pipeline
```

The pipeline runs: scrape → enrich → digest → rank → email.

## Troubleshooting

- Docker Compose variables not found:
  Docker Compose reads `.env` relative to where you run `docker compose` (or use `--env-file`).
- Connection string issues with special characters in passwords:
  URL-encode the password when building the SQLAlchemy connection URL.
- YouTube transcripts missing:
  Some videos disable transcripts; those entries are marked unavailable and skipped for transcript-based digesting.
- Gmail authentication fails:
  Ensure 2FA is enabled and you are using a Gmail app password.

## License

Add a license if you plan to make the project reusable (MIT is a common choice). If omitted, default GitHub rules apply.
