# AI News Aggregator

AI News Aggregator is an end-to-end Python pipeline that collects AI-related updates from multiple sources, stores them in PostgreSQL, enriches content when possible, generates structured digests with Gemini, ranks them for a user profile, and sends a daily email newsletter.

This project is built as a modular pipeline with separate layers for scraping, persistence, enrichment, digest generation, ranking, and email delivery.

---

## What the project does

High-level flow:

1. Scrape recent items from multiple sources
2. Store raw records in PostgreSQL
3. Enrich source content when possible
   - Anthropic articles → markdown
   - YouTube videos → transcripts
   - OpenAI news → RSS description
4. Generate digests for items that do not yet have one
5. Rank recent digests for a user profile
6. Generate and send a daily email digest

---

## Features

- Multi-source ingestion
  - YouTube uploads via RSS
  - OpenAI news via RSS
  - Anthropic articles via RSS + webpage-to-markdown extraction
- PostgreSQL persistence
- Content enrichment
  - YouTube transcripts via `youtube-transcript-api`
  - Anthropic article markdown via `docling`
- Digest generation with Gemini
- Personalized ranking for a user profile
- HTML + plain text email delivery through Gmail SMTP
- One-command pipeline execution through `main.py`

---

## Current source behavior

### YouTube
- Scrapes recent uploads from configured channels
- Attempts to fetch transcripts
- Falls back when transcripts are unavailable

### OpenAI
- Uses the RSS feed as the source of truth
- Stores title, description, URL, category, and publish date
- Does **not** depend on full-page scraping

### Anthropic
- Scrapes feed entries
- Attempts webpage-to-markdown extraction for richer content

---

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
│   └── runner.py
├── docker/
│   ├── .env
│   └── docker-compose.yaml
├── main.py
├── pyproject.toml
└── README.md
```

---

## Tech stack

- Python 3.11+
- PostgreSQL
- SQLAlchemy
- Pydantic
- Google Gemini
- feedparser
- Docling
- youtube-transcript-api
- markdown
- Gmail SMTP

---

## Setup

### 1. Start PostgreSQL

From the `docker/` directory:

```bash
docker compose up -d
```

Check that the container is running:

```bash
docker ps
```

---

### 2. Install dependencies

Using `uv`:

```bash
uv sync
```

---

### 3. Configure environment variables

The project currently uses:

- `docker/.env` for Docker Compose database values
- `app/.env` for application values

This works, but for a cleaner setup you can eventually move to a single root `.env` plus a `.env.example` template.

Example application environment variables:

```env
CURATOR_GEMINI_API_KEY=your_curator_key
DIGEST_GEMINI_API_KEY=your_digest_key
EMAIL_GEMINI_API_KEY=your_email_key

EMAIL=your_email@gmail.com
APP_PASSWORD=your_gmail_app_password

POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=ai_news_aggregator
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

PROXY_USERNAME=
PROXY_PASSWORD=
```

### Notes
- `EMAIL` is currently used as both sender and default recipient.
- Do not commit real `.env` files.
- For Gmail, use an App Password, not your normal password.

---

### 4. Create database tables

Run:

```bash
python -m app.database.create_tables
```

If you prefer `uv`:

```bash
uv run -m app.database.create_tables
```

---

## Usage

### Run the full pipeline

```bash
python main.py
```

You can also pass custom values:

```bash
python main.py 24 10
```

Where:
- `24` = number of hours to look back
- `10` = number of top ranked articles to include in the email

---

## Pipeline stages

The full pipeline performs:

1. Source scraping
2. Anthropic markdown enrichment
3. YouTube transcript enrichment
4. Digest generation
5. Ranking + email generation
6. Email sending

---

## Development notes

### Running style

Right now, the project is designed so that running `main.py` from the repository root is enough to execute the full pipeline.

If you want cleaner imports long-term, prefer module execution for standalone scripts:

```bash
python -m app.services.process_anthropic
python -m app.services.process_youtube
python -m app.services.process_digest
python -m app.services.process_email
```


### Current limitations

- OpenAI articles currently use RSS descriptions rather than full extracted article text
- Some YouTube videos do not expose transcripts
- Source richness is not uniform across providers

---

## Troubleshooting

### PostgreSQL connection issues
- Make sure Docker is running
- Make sure the container is healthy
- Verify the database values in your environment files

### Gmail authentication errors
- Enable 2FA on the Gmail account
- Use a valid Gmail App Password

### Missing YouTube transcripts
- Some videos disable transcripts
- Those videos may be skipped or marked unavailable

---

## Future improvements

Ideas for version 2:

- story deduplication across sources
- clustering related updates into a single story
- persistent user profiles
- dashboard / UI
- ingestion analytics
- source quality tracking
- better retry and failure-state handling

---

## License

All rights reserved.
