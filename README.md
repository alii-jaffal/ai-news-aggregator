# AI News Aggregator

AI News Aggregator is a Python pipeline that collects recent AI updates from multiple sources, stores them in PostgreSQL, enriches the content when possible, clusters related coverage into stories, generates story-level digests with Gemini, ranks them for an active user profile, and sends a daily email newsletter.

The project now also includes a local FastAPI + React dashboard for demoing the system, browsing historical data, inspecting failures, and triggering safe no-email reruns.

## What the project does

High-level flow:

1. Scrape recent source items from YouTube, OpenAI, and Anthropic feeds.
2. Store raw source records in PostgreSQL.
3. Enrich source content where possible.
   - YouTube videos -> transcript text when available
   - Anthropic articles -> markdown extracted from the page
   - OpenAI articles -> RSS title/description metadata
4. Cluster related source items into story records.
5. Generate one canonical digest per story.
6. Rank recent story digests against the active DB-backed user profile.
7. Generate a newsletter snapshot and optionally send it by email.
8. Persist pipeline run history and newsletter snapshots for the dashboard.

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
  |- YouTube RSS
  |- OpenAI RSS
  `- Anthropic RSS
        |
        v
Scrapers
        |
        v
PostgreSQL source tables
        |
        +--> Anthropic markdown enrichment
        +--> YouTube transcript enrichment
        |
        v
Story clustering
        |
        v
Story digests with Gemini
        |
        v
Ranking + newsletter generation
        |
        +--> SMTP email delivery
        `--> Pipeline/newsletter history tables
                    |
                    v
            FastAPI dashboard API
                    |
                    v
             React demo interface
```

## Project structure

```text
.
├── alembic/
├── app/
│   ├── agent/
│   ├── api/
│   ├── database/
│   ├── profiles/
│   ├── scrapers/
│   ├── services/
│   ├── content_normalization.py
│   ├── daily_runner.py
│   ├── logging_config.py
│   ├── runner.py
│   ├── settings.py
│   ├── story_clustering.py
│   └── story_digesting.py
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── tests/
├── main.py
├── pyproject.toml
└── README.md
```

## Tech stack

- Python 3.11+
- PostgreSQL
- SQLAlchemy
- Alembic
- FastAPI
- React + TypeScript + Vite
- Pydantic
- Google Gemini
- feedparser
- youtube-transcript-api
- Docling
- Gmail SMTP
- Docker / Docker Compose

## Quick start

### 1. Install Python dependencies

```bash
uv sync
```

### 2. Create a root `.env`

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

```bash
docker compose -f docker/docker-compose.yaml up -d
```

### 4. Apply database migrations

```bash
uv run alembic upgrade head
```

This creates the current schema, including:

- source tables
- story and story digest tables
- DB-backed user profiles
- pipeline run history
- newsletter snapshot history

### 5. Run the full CLI pipeline

```bash
uv run .\main.py
```

Optional arguments:

```bash
uv run .\main.py 24 10
```

Where:

- `24` = hours to look back
- `10` = top-ranked items to include

If the second argument is omitted, the pipeline uses `newsletter_top_n` from the active user profile.

## Dashboard setup

### 1. Install frontend dependencies

```bash
cd frontend
npm install
```

### 2. Run the FastAPI backend

From the repo root:

```bash
uv run uvicorn app.api.main:app --reload
```

### 3. Run the React frontend

From `frontend/`:

```bash
npm run dev
```

The React app expects the FastAPI API at `http://127.0.0.1:8000/api` by default.

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
uv run -m app.services.process_story_clusters
uv run -m app.services.process_story_digests
uv run -m app.services.process_email
```

### Run the dashboard API

```bash
uv run uvicorn app.api.main:app --reload
```

### Manage user profiles

```bash
uv run -m app.profiles.manage_profiles list
uv run -m app.profiles.manage_profiles show-active
uv run -m app.profiles.manage_profiles upsert --slug default --name "Ali Jaffal" --title "AI Engineer & Researcher" --background "Experienced AI engineer focused on practical systems" --expertise-level Intermediate --interest "AI agents" --preferred-source-type youtube --preferred-source-type openai --preferred-source-type anthropic --preference prefer_practical=true --newsletter-top-n 10 --active
uv run -m app.profiles.manage_profiles set-active default
```

The legacy `app/profiles/user_profile.py` file is now only used to seed the first profile automatically.

## Dashboard behavior

- The dashboard is local-only in v1.
- Dashboard-triggered reruns create pipeline history rows and newsletter snapshots.
- Dashboard-triggered reruns do **not** send email.
- CLI-triggered runs keep normal email behavior.

## Tests

Run backend tests:

```bash
uv run pytest
```

Run frontend tests:

```bash
cd frontend
npm run test
```

## Known limitations

- OpenAI entries currently use RSS metadata rather than full article extraction.
- Some YouTube videos have no transcript available.
- Gemini calls can occasionally fail with temporary `503 UNAVAILABLE` responses during high demand.
- The dashboard is intended for local demo/admin use and does not include authentication in v1.
- The first dashboard version uses filter-based archive browsing rather than full-text search across all cleaned content.

## Troubleshooting

### Database connection fails

Check:

- PostgreSQL is running
- root `.env` values are correct
- `POSTGRES_HOST` is correct for your setup
- `uv run alembic upgrade head` completed successfully

### No transcripts were processed

Possible reasons:

- the newly scraped videos already had transcripts stored
- the videos do not expose transcripts
- transcript retrieval is rate-limited or blocked

### Digest generation or ranking fails with `503`

This is usually a temporary Gemini availability issue, not a project import/config problem. Re-run the stage later.

### Email fails

Check:

- `EMAIL` and `APP_PASSWORD` are set correctly
- the Gmail app password is valid
- the ranking step succeeded

### Dashboard rerun looks successful but no email arrived

That is expected. Dashboard reruns intentionally store results without sending email.

## Duplicate handling and rerun safety

The pipeline is designed to be rerun safely for the same time window.

- YouTube videos are deduplicated by `video_id`
- OpenAI articles are deduplicated by `guid`
- Anthropic articles are deduplicated by `guid`
- story digests are reused when the digest input hash is unchanged

Source ingestion uses batch existence checks before inserts, so repeated runs do not create duplicate rows.

Enrichment and digest stages use explicit status fields, and dashboard reruns are guarded so only one API-triggered run can be active at a time.
