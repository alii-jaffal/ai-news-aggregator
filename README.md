# AI News Aggregator

AI News Aggregator is a Python project that collects recent AI updates from multiple sources, stores them in PostgreSQL, enriches the content when possible, generates short digests with Gemini, ranks those digests for a user profile, and sends a daily email newsletter in both plain text and HTML.

The project is built as a pipeline, not a single script. It has separate layers for scraping, persistence, enrichment, digest generation, ranking, and email delivery.

## What the project does

High-level flow:

1. Scrape recent items from configured sources.
2. Store raw source records in PostgreSQL.
3. Enrich source content where possible.
   - YouTube videos -> transcript text when available
   - Anthropic articles -> markdown extracted from the page
   - OpenAI articles -> RSS title/description metadata
4. Generate digest records for items that do not already have one.
5. Rank recent digests against the project’s user profile.
6. Generate and send a daily email digest.

## Current sources

### YouTube
- Source type: RSS channel feeds
- Stored data: video id, title, url, channel id, publish time, description
- Enrichment: transcript retrieval with `youtube-transcript-api`
- Limitation: some videos do not expose transcripts

### OpenAI
- Source type: RSS feed
- Stored data: guid, title, url, publish time, description, category
- Enrichment: none beyond feed metadata
- Limitation: this source currently relies on RSS title/description rather than full article scraping

### Anthropic
- Source type: RSS feed entries
- Stored data: guid, title, url, publish time, description, category
- Enrichment: webpage -> markdown extraction using Docling
- Limitation: extraction quality depends on the source page structure

## Architecture

```text
Sources
  ├─ YouTube RSS
  ├─ OpenAI RSS
  └─ Anthropic RSS
        |
        v
Scrapers
        |
        v
PostgreSQL raw tables
        |
        +--> Anthropic markdown enrichment
        |
        +--> YouTube transcript enrichment
        |
        v
Digest generation with Gemini
        |
        v
Digest table
        |
        v
Ranking with Gemini curator
        |
        v
Email introduction + HTML rendering + SMTP delivery
```

## Project structure

```text
.
├── app/
│   ├── agent/
│   │   ├── curator_agent.py
│   │   ├── digest_agent.py
│   │   └── email_agent.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── create_tables.py
│   │   ├── models.py
│   │   └── repository.py
│   ├── profiles/
│   │   └── user_profile.py
│   ├── scrapers/
│   │   ├── anthropic.py
│   │   ├── openai.py
│   │   └── youtube.py
│   ├── services/
│   │   ├── email_service.py
│   │   ├── process_anthropic.py
│   │   ├── process_curator.py
│   │   ├── process_digest.py
│   │   ├── process_email.py
│   │   └── process_youtube.py
│   ├── config.py
│   ├── daily_runner.py
│   ├── runner.py
│   └── settings.py
├── docker/
│   └── docker-compose.yaml
│   
├── main.py
├── pyproject.toml
└── README.md
```

## Tech stack

- Python 3.11+
- PostgreSQL
- SQLAlchemy
- Pydantic
- pydantic-settings
- Google Gemini
- feedparser
- youtube-transcript-api
- Docling
- markdown
- Gmail SMTP
- Docker / Docker Compose

## Quick start

### 1. Install dependencies

```bash
uv sync
```

### 2. Create a single root `.env`

Create `.env` in the project root.

```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_news_aggregator

# Gemini API keys
DIGEST_GEMINI_API_KEY=your_digest_key
CURATOR_GEMINI_API_KEY=your_curator_key
EMAIL_GEMINI_API_KEY=your_email_key

# Email
EMAIL=your_email@gmail.com
APP_PASSWORD=your_gmail_app_password

# Optional proxy for transcript retrieval
PROXY_USERNAME=
PROXY_PASSWORD=
```

### 3. Start PostgreSQL

Use whichever workflow you prefer:

#### Option A: Docker Compose

```bash
docker compose -f docker/docker-compose.yaml up -d
```

#### Option B: Docker Desktop
Start the existing Postgres container from Docker Desktop after it has been created from the compose file.

### 4. Create tables

```bash
uv run -m app.database.create_tables
```

### 5. Run the full pipeline

```bash
uv run .\main.py
```

Optional arguments:

```bash
uv run .\main.py 24 10
```

Where:
- `24` = hours to look back
- `10` = number of top ranked articles to include in the email

## Official commands

### Full pipeline

```bash
uv run .\main.py
```

### Scraping only

```bash
uv run -m app.runner
```

### Re-run individual stages

```bash
uv run -m app.services.process_anthropic
uv run -m app.services.process_youtube
uv run -m app.services.process_digest
uv run -m app.services.process_email
```

## Known limitations

- OpenAI entries currently use RSS metadata rather than full article extraction.
- Some YouTube videos have no transcript available.
- Gemini calls can occasionally fail with temporary `503 UNAVAILABLE` responses during high demand.
- Ranking and email generation currently depend on successful LLM calls.

## Troubleshooting

### Database connection fails
Check:
- PostgreSQL container is running
- root `.env` values are correct
- `POSTGRES_HOST` is correct for your setup
- tables were created successfully

### No transcripts were processed
Possible reasons:
- the newly scraped videos already had transcripts stored
- the videos do not expose transcripts
- transcript retrieval is rate-limited or blocked

### Digest generation or ranking fails with 503
This is usually a temporary Gemini availability issue, not a project import/config problem. Re-run the stage later.

### Email fails
Check:
- `EMAIL` and `APP_PASSWORD` are set correctly
- Gmail app password is valid
- the ranking step succeeded

## Future improvement areas

- retry and fallback handling for Gemini failures
- story deduplication across sources
- richer source analytics and failure tracking
- persistent user preferences
- web dashboard for browsing archived digests
