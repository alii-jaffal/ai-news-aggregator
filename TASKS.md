# AI News Aggregator
## Project Improvement Task Document

> Team implementation plan for improving the existing Python/AI project

_Prepared for teammates and collaborators_

## At a Glance

| Item | Details |
|---|---|
| **Project focus** | Improve and professionalize the existing AI News Aggregator rather than replacing it with a new idea. |
| **Document purpose** | Turn the improvement plan into concrete tasks that can be assigned to teammates and completed in a logical order. |
| **Recommended use** | Use this document as the main planning handoff: assign tasks, track progress, and keep advanced features visible for later phases. |
| **Difficulty scale** | Easy = low risk and fast to implement; Medium = moderate engineering work; Hard = deeper design or database changes; Advanced = major product/AI feature work. |

## Overview

The project already has a strong foundation: it collects AI updates from multiple sources, stores them in PostgreSQL, enriches content where possible, generates digests, ranks items, and sends an email brief. The next goal is to evolve it from a solid personal project into a cleaner, more reliable, and more product-like system. The tasks below are ordered so the team can strengthen the foundation first, then improve intelligence quality, and finally add advanced features.

## Recommended Build Order

| Phase | Main objective | Task range |
|---|---|---|
| **Phase 1** | Stabilize structure, config, and onboarding | Tasks 1-4 |
| **Phase 2** | Improve reliability, data quality, and maintainability | Tasks 5-8 |
| **Phase 3** | Upgrade intelligence quality and story-level reasoning | Tasks 9-11 |
| **Phase 4** | Productize the system and add advanced features | Tasks 12-14 |

---

## Phase 1 — Foundation and Developer Experience

### Task 1 — Standardize Package Execution and Remove Path Hacks

**Difficulty:** `Medium`

**Goal**

> Make the project run through clean package-based commands so teammates do not depend on manual import fixes or fragile local setups.

**Exact work to do**

- Audit the current entry points and confirm which commands the team should officially support, starting with the existing main.py workflow.
- Keep the project runnable from the repository root and move the team toward module-based execution for internal scripts, such as python -m app.database.create_tables and python -m app.services.process_digest.
- Remove sys.path.insert(...) only from files that no longer need it after testing the official run commands. The current cleanup candidates are app/database/create_tables.py, app/services/process_anthropic.py, app/services/process_curator.py, app/services/process_digest.py, and app/services/process_youtube.py.
- Verify that package markers such as __init__.py files are present wherever needed so imports behave consistently.
- Test the full pipeline after cleanup to make sure the import changes do not break the normal project workflow.

**Expected outcome**

The project runs in a predictable way from the repository root, imports are cleaner, and new contributors no longer need to understand or maintain custom path injections.

> ---

### Task 2 — Consolidate Environment Variables and Central Configuration

**Difficulty:** `Medium`

**Goal**

> Create one clear source of truth for runtime configuration so secrets, database settings, and service credentials are easy to manage and hard to misuse.

**Exact work to do**

- Move toward a single root-level .env file for real values and a root-level .env.example file for onboarding and safe sharing.
- Standardize naming for environment variables such as POSTGRES_*, EMAIL, APP_PASSWORD, and Gemini API keys so the same names appear in code, documentation, and deployment configuration.
- Update Docker Compose to read the root environment file explicitly, or document the exact command that should be used when the compose file lives in a subfolder.
- Centralize environment loading through one config module instead of scattered os.getenv calls wherever practical.
- Remove duplicate or outdated .env files only after the team has verified that local runs, Docker startup, and email delivery still work correctly.

**Expected outcome**

Configuration becomes easier to understand, easier to document, and safer for collaborators. The project avoids silent drift between app settings and Docker settings.

> ---

### Task 3 — Rewrite the README and Add a Contributor Runbook

**Difficulty:** `Easy to Medium`

**Goal**

> Make the repository self-explanatory so a teammate can clone it, understand it, and run it without returning to chat for setup guidance.

**Exact work to do**

- Replace outdated README content with the real project structure, actual commands, current source behavior, and known limitations.
- Document the exact startup order: database, dependency installation, table creation if needed, full pipeline run, and troubleshooting steps.
- Explicitly note source differences, including that OpenAI currently uses RSS title/description metadata rather than full article scraping.
- Add a short contributor runbook that explains where to put secrets, how to run tests, how to re-run a failed stage, and which commands are considered official.
- Include a small architecture section so teammates understand the data flow from scraping to digest generation to ranking and email delivery.

**Expected outcome**

The repository becomes shareable in a normal way. Teammates can open the project, read one document, and get started with much less friction.

> ---

### Task 4 — Add Structured Logging and Run-Level Observability

**Difficulty:** `Medium`

**Goal**

> Make pipeline runs debuggable and measurable so the team can quickly understand what happened during a scrape, enrichment pass, or email generation run.

**Exact work to do**

- Introduce one centralized logging setup used by all pipeline stages instead of ad hoc print statements.
- Log important events consistently: start time, end time, source counts, skipped items, failures, retry attempts, and email send results.
- Attach a run identifier or timestamp to each full pipeline execution so related log lines can be grouped during debugging.
- Separate expected informational messages from warnings and real errors to improve signal quality.
- Optionally persist logs or summary statistics so failed runs can be investigated after the process exits.

**Expected outcome**

When something breaks or produces weak output, the team can inspect the logs and immediately see where the failure happened and how much data was affected.

> ---

---

## Phase 2 — Reliability, Data Quality, and Maintainability

### Task 5 — Normalize Database Status Fields and Content Metadata

**Difficulty:** `Medium to Hard`

**Goal**

> Replace ambiguous or magic-string pipeline state with explicit structured fields that clearly describe enrichment success, failure, and content quality.

**Exact work to do**

- Add explicit status fields such as transcript_status, markdown_status, digest_status, and content_richness to the relevant database models.
- Store useful metadata alongside those fields, for example transcript length, cleaned content length, failure reason, last processed time, and source type.
- Add the necessary migration or schema update process so the database evolves cleanly instead of relying on manual edits.
- Update repository methods and service scripts so they read and write the new fields consistently.
- Backfill older rows where possible so existing data remains useful after the schema change.

**Expected outcome**

The team can inspect the database and immediately understand what happened to each item, why some items were skipped, and how rich each source actually is.

> ---

### Task 6 — Improve Repository Efficiency, Idempotency, and Duplicate Handling

**Difficulty:** `Hard`

**Goal**

> Make repeated runs safe and efficient so the pipeline can be rerun without creating duplicates or wasting time on row-by-row checks.

**Exact work to do**

- Add or review unique constraints and indexes for source-specific identifiers such as URLs, feed item IDs, or video IDs.
- Replace repetitive existence checks with batch operations or upsert-style logic wherever the database and ORM support it.
- Ensure each stage can be rerun safely for the same time window without creating duplicate stored items or duplicate digests.
- Measure which repository operations are currently the slowest and refactor those hotspots first.
- Document how the project handles duplicate source items, reprocessing, and partial reruns so the behavior is intentional rather than accidental.

**Expected outcome**

The project becomes more scalable and safer to operate. Teammates can rerun failed windows or experiment with changes without corrupting the dataset.

> ---

### Task 7 — Build a Test Suite for the Core Pipeline

**Difficulty:** `Medium to Hard`

**Goal**

> Protect the project from regressions by adding enough tests to cover the most important behavior without over-testing trivial code.

**Exact work to do**

- Add unit tests for the highest-value logic first: feed parsing, repository behavior, config loading, and content cleaning utilities.
- Mock external dependencies such as Gemini, SMTP, and network calls so tests stay cheap and deterministic.
- Add smoke tests that verify the main pipeline can start and that key stages can be executed in sequence in a controlled environment.
- Configure linting, formatting, and test commands so collaborators run the same checks locally before pushing changes.
- Decide which failures should block merges, for example import errors, parser regressions, or broken digest validation.

**Expected outcome**

The team can refactor with confidence. Important breakages are caught early instead of being discovered only after a failed newsletter run.

> ---

### Task 8 — Standardize Content Ingestion and Source Quality Handling

**Difficulty:** `Medium`

**Goal**

> Create a consistent internal representation of source content so downstream digest generation receives cleaner and more comparable inputs.

**Exact work to do**

- Define normalized content fields that every source will populate, such as raw_title, raw_summary, cleaned_content, publish_date, content_length, and source_type.
- Keep the OpenAI source honest and intentional by treating it as a metadata-rich RSS source rather than forcing unreliable full-page scraping.
- Continue using Anthropic webpage-to-markdown extraction where it works, and keep transcript retrieval for YouTube while tracking transcript availability explicitly.
- Apply common cleaning rules for markdown, transcripts, truncation, whitespace normalization, and fallback summaries.
- Record source-quality metadata so later ranking or digest logic can distinguish between transcript-rich, markdown-rich, and summary-only inputs.

**Expected outcome**

Digest generation receives better structured input, and the project becomes more transparent about which sources provide deep content versus shallow metadata.

> ---

---

## Phase 3 — Intelligence Upgrades

### Task 9 — Add Story Deduplication and Clustering

**Difficulty:** `Hard`

**Goal**

> Reduce repeated coverage by grouping related articles and videos into a single story instead of treating every source item as independent.

**Exact work to do**

- Generate embeddings or another similarity representation for recent source items after ingestion and cleaning.
- Define a clustering strategy for recent items, including similarity thresholds, time-window rules, and fallback logic when confidence is low.
- Store story or cluster records in the database so the grouping can be inspected, reranked, and reused later.
- Keep source-to-story links so each story still knows which articles, blog posts, or videos support it.
- Evaluate clustering quality on real project data and tune the thresholds to minimize false merges and obvious duplicates.

**Expected outcome**

The email brief becomes less repetitive, and the project starts to look like an intelligent news system rather than a list of unrelated scraped items.

> ---

### Task 10 — Generate Multi-Source Story-Level Digests

**Difficulty:** `Hard to Advanced`

**Goal**

> Upgrade the digest layer from summarizing single inputs to synthesizing multiple sources about the same story into one stronger output.

**Exact work to do**

- Use the new story clusters as the unit of summarization instead of individual source items whenever enough evidence is available.
- Design a structured prompt and output schema that captures what happened, why it matters, supporting sources, and any disagreements between sources.
- Preserve source attribution so the final output can still link back to the original OpenAI, Anthropic, and YouTube items that informed the story.
- Rank stories, not just articles, so the newsletter focuses on the best topics rather than whichever source produced the most items.
- Compare the quality of story-level digests against the current article-level approach and keep fallback behavior for sparse clusters.

**Expected outcome**

This becomes one of the project's standout features: a single ranked brief can summarize a real story across multiple AI sources instead of repeating the same topic several times.

> ---

### Task 11 — Replace the Hardcoded User Profile with Persistent Personalization

**Difficulty:** `Hard`

**Goal**

> Turn ranking into a more realistic personalized system by storing user preferences instead of hardcoding one static profile in code.

**Exact work to do**

- Create a database-backed user profile model with fields such as preferred topics, preferred source types, technical depth, and desired number of newsletter items.
- Refactor ranking so it reads from stored profile data instead of a fixed Python dictionary.
- Allow simple profile editing through configuration, a JSON file, a small admin script, or a basic API endpoint depending on implementation scope.
- Keep the design extensible so future feedback signals such as clicks, likes, or manual topic weights can be added later without a redesign.
- Test how ranking changes when different user profiles are applied to the same source window.

**Expected outcome**

The project moves from a personal script toward a real product pattern: the same pipeline can serve more than one preference profile and produce meaningfully different results.

> ---

---

## Phase 4 — Productization and Advanced Expansion

### Task 12 — Add Analytics, Archive Browsing, and a Demo-Friendly Interface

**Difficulty:** `Hard to Advanced`

**Goal**

> Make the project easier to demo, inspect, and manage by exposing the data and pipeline state through a simple interface or API.

**Exact work to do**

- Choose a lightweight presentation layer such as FastAPI plus a basic frontend, Streamlit, or a simple internal dashboard.
- Expose useful views: recent source items, recent stories, failed jobs, source counts, top ranked outputs, and processing history.
- Add archive browsing or search so the team can inspect historical runs instead of relying only on received emails.
- Include simple operational actions if helpful, such as retrying a stage, rerunning a recent window, or marking an item for reprocessing.
- Keep the first version narrow and pragmatic so it improves demos without becoming a separate large product.

**Expected outcome**

The project becomes much easier to show on a portfolio, explain to teammates, and operate during debugging or live demos.

> ---

### Task 13 — Add Trend Detection and Weekly Intelligence Reports

**Difficulty:** `Advanced`

**Goal**

> Move beyond daily summarization and turn the system into a lightweight AI intelligence product that highlights what is rising over time.

**Exact work to do**

- Tag items or stories with themes such as agents, multimodal models, reasoning, open-source releases, infrastructure, or enterprise tools.
- Track theme frequency over time and compare recent windows against earlier windows to identify rising topics.
- Generate a weekly or periodic report that explains major trends rather than only listing isolated news items.
- Include evidence for each trend, such as linked stories, source counts, and representative summaries.
- Evaluate whether trend outputs feel genuinely informative and avoid reporting noise as if it were a real shift.

**Expected outcome**

The project gains a higher-value analytical layer that is stronger for demos, portfolios, and future product expansion than a simple daily recap alone.

> ---

### Task 14 — Prepare the Project for Reliable Scheduled Deployment

**Difficulty:** `Medium to Hard`

**Goal**

> Run the system automatically and safely so it behaves like a service rather than something that only works when launched manually from a development machine.

**Exact work to do**

- Package the runtime and startup process clearly so the project can be scheduled in one consistent way across environments.
- Choose a scheduling approach such as cron, a cloud scheduler, GitHub Actions, or a small hosted worker depending on budget and deployment goals.
- Document how secrets will be provided in deployment and how failures will be surfaced to the team.
- Add basic health checks or failure notifications so a broken run is noticed quickly.
- Test the scheduled workflow end to end, including database connectivity, digest generation, ranking, and email delivery.

**Expected outcome**

The project becomes operationally credible: it can run on a schedule, fail visibly, and support consistent demos or production-style usage.

> ---

## Suggested Team Assignment Strategy

**A practical team split would be:** one person on project structure and configuration (Tasks 1-3), one person on reliability and database work (Tasks 4-7), one person on intelligence upgrades (Tasks 8-11), and the advanced productization work (Tasks 12-14) only after the earlier tasks are stable.

**Implementation note:** these tasks are sequenced so the team strengthens the foundation before building advanced AI features.