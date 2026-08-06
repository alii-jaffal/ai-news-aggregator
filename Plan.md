# AI News Aggregator — Production Product Roadmap

## Purpose

This document defines the work required to evolve the current AI News Aggregator from a portfolio-style admin application into a polished, customer-facing, production-ready newsletter product.

The target product is:

> A weekly AI news briefing for AI professionals that combines duplicate coverage, summarizes the strongest sources, and prioritizes stories based on each user's interests.

This roadmap focuses on **what each task means**, **why it matters**, and **what should be true after it is completed**. It intentionally avoids prescribing low-level implementation details so an implementation agent can choose the technical approach without drifting from the intended outcome.

The locked v1 product definition for this roadmap lives in `PRODUCT_SCOPE.md`.

---

## Product principles

1. **Weekly first:** Launch with one weekly newsletter frequency.
2. **Global processing, personal delivery:** Scrape, enrich, cluster, and summarize once globally; personalize only ranking and delivery per user.
3. **Public product plus private operations:** Build a customer-facing site and keep the current dashboard as a private admin console.
4. **Reliable by default:** Retries must be safe, duplicate email delivery must be prevented, and failed jobs must be recoverable.
5. **Simple onboarding:** Registration and interest selection should take only a few clear steps.
6. **Keep the current scraping approach:** Feedparser remains the discovery layer; existing enrichment and fallbacks remain in place.

---

# Phase 1 — Product definition and customer experience

## Task 1 — Define the initial product scope

**Difficulty:** 3/10  
**Importance:** 10/10  
**Priority:** Launch-critical

### What this task means

Define the exact first version of the product before adding more features.

Recommended first version:

- Weekly newsletter only
- English only
- 7 stories
- Free private beta
- Target audience: AI professionals
- Personalized by interests and expertise level
- Duplicate coverage combined into one canonical story

### Expected outcome

- The product has one clear promise.
- Engineering and design choices can be evaluated against that promise.
- Daily newsletters, mobile apps, billing, teams, and unrelated features do not delay launch.

### Completion criteria

- Product promise is documented.
- Frequency, newsletter size, language, and first target users are defined.
- Deferred features are explicitly listed.
- The roadmap references the locked v1 definition in `PRODUCT_SCOPE.md`.

---

## Task 2 — Create a professional public homepage

**Difficulty:** 6/10  
**Importance:** 9/10  
**Priority:** Launch-critical

### What this task means

Replace the admin-oriented first impression with a customer-facing landing page.

The page should explain:

- What the service does
- Why it is useful
- How it combines duplicate news
- How personalization works
- What sources it covers
- What a sample newsletter looks like
- How to subscribe

Suggested value proposition:

> The AI news that matters—without reading the same story five times.

### Expected outcome

- Visitors immediately understand the product.
- The application looks like a real newsletter service.
- Users can move naturally from the homepage into registration.
- The current dashboard is no longer the public landing page.

### Completion criteria

- Homepage contains a clear headline, benefits, product explanation, sample newsletter, and subscribe action.
- It works well on desktop and mobile.
- Admin operations are not exposed publicly.

---

## Task 3 — Build real user authentication

**Difficulty:** 7/10  
**Importance:** 10/10  
**Priority:** Launch-critical

### What this task means

Replace the shared admin credentials with real user accounts.

Users should be able to:

- Register
- Log in and log out
- Verify their email
- Reset a forgotten password
- Change their password
- Delete their account

Admin permissions must remain separate from customer permissions.

### Expected outcome

- Every subscriber has an independent account.
- Preferences and newsletters belong to the correct user.
- Customers cannot access administrative operations.
- Authentication is suitable for a public product.

### Completion criteria

- Registration, login, logout, email verification, and password reset work.
- Sessions expire safely.
- Normal-user and admin permissions are separated.
- Account deletion is supported.

---

## Task 4 — Build a simple interest-onboarding flow

**Difficulty:** 6/10  
**Importance:** 10/10  
**Priority:** Launch-critical

### What this task means

After registration, guide the user through a short personalization flow.

Possible interests:

- Large language models
- AI agents
- Open-source AI
- AI coding tools
- AI research
- Computer vision
- Robotics
- AI startups and funding
- Enterprise AI
- AI regulation

Also collect:

- Expertise level
- Preferred content style
- Optional preferred sources

### Expected outcome

- New users can personalize their newsletter quickly.
- The system has enough information to rank stories.
- Onboarding feels clean and non-technical.
- Completing onboarding activates the subscription.

### Completion criteria

- Onboarding uses only a small number of screens.
- Interests, expertise level, and content style are saved.
- Unnecessary configuration is avoided.
- The user is subscribed after completion.

---

## Task 5 — Add account and subscription settings

**Difficulty:** 5/10  
**Importance:** 9/10  
**Priority:** Launch-critical

### What this task means

Provide a customer account area for managing preferences and subscription state.

Users should be able to:

- Edit interests
- Change expertise level and content style
- Pause newsletters
- Resume newsletters
- Unsubscribe
- Change email and password
- Delete their account
- View previous newsletters

### Expected outcome

- Users can manage their subscription without administrator help.
- Subscription state is visible and controllable.
- Newsletter history is accessible.

### Completion criteria

- Account page exists.
- Preferences can be edited.
- Subscription can be paused, resumed, and cancelled.
- Past newsletters can be viewed.
- Account deletion works.

---

# Phase 2 — Multi-user data and pipeline architecture

## Task 6 — Redesign the database for multiple users

**Difficulty:** 7/10  
**Importance:** 10/10  
**Priority:** Launch-critical

### What this task means

Replace the current single-active-profile concept with a proper multi-user data model.

The database should represent:

- Users
- User preferences
- User interests
- Subscription state
- Newsletter issues
- Email delivery attempts
- Verification and account status
- User newsletter history

Global source items, stories, clusters, and story digests remain shared across users.

### Expected outcome

- Many users can subscribe independently.
- Each user has separate interests and newsletter history.
- Expensive AI processing remains shared.
- Delivery records can be tracked per subscriber.

### Completion criteria

- No customer workflow depends on one global active profile.
- Users, preferences, interests, subscriptions, newsletters, and deliveries have correct relationships.
- Uniqueness rules prevent duplicate subscriptions and duplicate newsletter issues.

---

## Task 7 — Separate global processing from user personalization

**Difficulty:** 8/10  
**Importance:** 10/10  
**Priority:** Launch-critical

### What this task means

Split the current pipeline into two systems.

### Global pipeline

Runs once for all users:

- Discover source items
- Enrich and normalize content
- Generate embeddings
- Cluster duplicate stories
- Generate canonical story digests

### Per-user pipeline

Runs for each subscriber:

- Load eligible recent stories
- Rank them using user preferences
- Select the top stories
- Render a newsletter
- Queue email delivery

### Expected outcome

- More subscribers do not multiply scraping and summarization costs.
- Expensive content processing is shared.
- Only personalization and delivery scale with user count.
- The architecture can support a real subscription product.

### Completion criteria

- Global processing runs without a user profile.
- Story digests are generated once and reused.
- Per-user tasks do not rescrape sources or regenerate all digests.

---

## Task 8 — Keep and formalize the existing scraping layer

**Difficulty:** 3/10  
**Importance:** 8/10  
**Priority:** Launch-critical

### What this task means

Keep Feedparser and the current source-specific enrichment logic.

The ingestion layer should continue to:

- Discover RSS and Atom entries
- Preserve source IDs and GUIDs
- Avoid exact duplicates
- Retrieve transcripts or article content where available
- Fall back to RSS metadata when richer extraction fails

Docling may remain where already useful, but it should not replace Feedparser.

### Expected outcome

- Existing reliable scraping behavior is preserved.
- Discovery, enrichment, and fallback responsibilities are clearly defined.
- The project avoids an unnecessary ingestion rewrite.

### Completion criteria

- Feedparser remains the discovery layer.
- Existing source-specific enrichment continues to work.
- Fallback behavior is documented.
- No scraper rewrite is introduced without a measured need.

---

# Phase 3 — Background jobs, scheduling, and reliability

## Task 9 — Migrate background processing to Celery and Redis

**Difficulty:** 8/10  
**Importance:** 9/10  
**Priority:** Launch-critical

### What this task means

Replace the custom PostgreSQL-polling worker with a production task queue that supports separate task types, retries, scheduling, and multiple workers.

Celery executes background tasks. Redis acts as the broker. PostgreSQL remains the permanent source of truth.

Task categories may include:

- Ingestion
- Content enrichment
- AI processing
- Newsletter generation
- Email delivery
- Maintenance and recovery

### Expected outcome

- FastAPI submits long-running work instead of executing it directly.
- Different task types can use separate queues.
- Temporary failures can be retried safely.
- The system can add workers when load increases.

### Completion criteria

- Celery and Redis run successfully in Docker or Linux.
- Long-running work no longer depends on the custom polling loop.
- Pipeline and delivery state remain persisted in PostgreSQL.
- Existing functionality still works after migration.

### Important constraint

Celery is not officially supported as a native Windows production runtime. Local Windows development should use Docker or WSL2. Production should run Linux containers.

---

## Task 10 — Add recurring scheduling

**Difficulty:** 6/10  
**Importance:** 10/10  
**Priority:** Launch-critical

### What this task means

Automate ingestion, enrichment, clustering, digesting, and newsletter delivery.

Recommended scheduling model:

- Scrape new content several times per day
- Enrich newly discovered items
- Cluster stories and refresh digests regularly
- Periodically find subscriptions whose `next_send_at` has arrived
- Generate and send weekly newsletters for those users

Do not create one hardcoded scheduler entry per subscriber.

### Expected outcome

- The product operates without manual terminal commands.
- New content is processed automatically.
- Weekly newsletters are delivered on schedule.
- Delivery timing is controlled by subscription data.

### Completion criteria

- Scheduled jobs execute automatically.
- Only one scheduler instance creates periodic jobs.
- Due subscriptions are selected from PostgreSQL.
- Missed or delayed schedules are visible and recoverable.

---

## Task 11 — Make newsletter generation and email delivery idempotent

**Difficulty:** 8/10  
**Importance:** 10/10  
**Priority:** Launch-critical

### What this task means

Ensure retries cannot generate duplicate weekly issues or send the same email twice.

A newsletter issue should have a unique identity based on:

- User
- Newsletter type
- Covered period

An email delivery should have a unique identity based on:

- Newsletter issue
- Recipient

### Expected outcome

- Worker crashes and retries do not send duplicate emails.
- Repeated scheduler execution does not create duplicate issues.
- Delivery state is auditable.
- Failed deliveries can be retried safely.

### Completion criteria

- Reprocessing the same weekly period does not create another newsletter issue.
- A delivery already marked sent is not sent again.
- Unique constraints protect against duplicates.
- Crash-and-retry scenarios are covered by tests.

---

## Task 12 — Add centralized timeouts, retries, and rate-limit handling

**Difficulty:** 8/10  
**Importance:** 10/10  
**Priority:** Launch-critical

### What this task means

Standardize failure handling for Gemini, RSS feeds, websites, YouTube transcripts, Docling, the email provider, and future APIs.

The system should distinguish:

- Temporary errors
- Permanent errors
- Rate limits
- Invalid requests
- Provider outages

### Expected outcome

- One provider failure does not destroy the whole weekly process.
- Tasks do not retry forever.
- Workers do not all retry at the same moment.
- Slow calls cannot block workers indefinitely.
- Failed work remains visible and retryable.

### Completion criteria

- External calls have explicit timeouts.
- Retry counts are limited.
- Backoff and jitter are supported.
- `Retry-After` is respected when available.
- Permanent and temporary failures are handled differently.
- Failure reasons are persisted clearly.

---

## Task 13 — Add safe failed-task recovery

**Difficulty:** 7/10  
**Importance:** 9/10  
**Priority:** Launch-critical

### What this task means

Support recovery from worker crashes, server restarts, stuck work, and partially completed pipelines.

Work should have clear states such as:

- Queued
- Running
- Retrying
- Completed
- Failed
- Permanently failed
- Cancelled

### Expected outcome

- Jobs do not remain stuck forever.
- Operators can see why a task failed.
- Safe tasks can be retried.
- Successful work is not unnecessarily repeated.
- Infrastructure restarts are recoverable.

### Completion criteria

- Stale or abandoned work can be detected.
- Failed tasks can be retried from the admin area.
- Attempt counts and failure reasons are stored.
- Successful stages are preserved when possible.

---

# Phase 4 — Email product infrastructure

## Task 14 — Replace personal SMTP with a production email provider

**Difficulty:** 7/10  
**Importance:** 10/10  
**Priority:** Launch-critical

### What this task means

Use an email service designed for production applications instead of personal Gmail SMTP.

The service should support:

- Domain authentication
- Delivery tracking
- Bounce handling
- Complaint handling
- Suppression lists
- Provider message IDs
- HTML and plain-text email versions

### Expected outcome

- Newsletters come from a professional domain.
- Delivery can be tracked.
- Bounced and complaining recipients are handled.
- The product no longer depends on a personal mailbox.

### Completion criteria

- Production provider is integrated.
- Domain authentication is complete.
- Sent, delivered, bounced, complained, and failed states can be stored.
- Suppressed recipients are not repeatedly emailed.

---

## Task 15 — Add email verification, consent, and unsubscribe handling

**Difficulty:** 6/10  
**Importance:** 10/10  
**Priority:** Launch-critical

### What this task means

Require users to confirm their email and provide simple subscription controls.

Required behaviors:

- Email verification before newsletter delivery
- Explicit subscription consent
- One-click unsubscribe
- Pause and resume
- No automatic resubscription without user action

### Expected outcome

- Only verified, consenting users receive newsletters.
- Users can leave without contacting support.
- Complaint and deliverability risk is reduced.

### Completion criteria

- Verification links work.
- Unverified users are not sent newsletters.
- Every newsletter includes an unsubscribe mechanism.
- Unsubscribed users stop receiving mail.
- Subscription changes are auditable.

---

# Phase 5 — Private administration and operations

## Task 16 — Convert the existing dashboard into a private admin console

**Difficulty:** 5/10  
**Importance:** 8/10  
**Priority:** Launch-critical

### What this task means

Keep the useful current dashboard functionality but make it administrator-only.

It should support inspection of:

- Users and active subscriptions
- Source ingestion
- Story clusters
- Generated digests
- Newsletter issues
- Email failures
- Celery task status
- Worker and scheduler health
- AI usage and cost
- Manual retry operations

### Expected outcome

- Customers see a polished product interface.
- Administrators retain operational visibility.
- Failures can be investigated without direct database access.
- The existing dashboard remains useful.

### Completion criteria

- Admin area is protected by admin authorization.
- Customer accounts cannot access it.
- Existing run history and retry controls remain available.
- User, task, and delivery health can be inspected.

---

## Task 17 — Add monitoring, metrics, and alerts

**Difficulty:** 7/10  
**Importance:** 9/10  
**Priority:** Launch-critical

### What this task means

Make production health visible before users report problems.

Track:

- New source items
- Extraction failures
- Gemini errors
- Task duration
- Queue depth
- Worker availability
- Newsletter success
- Delivery success
- Bounce rate
- Token usage
- Estimated AI cost
- Cost per newsletter
- Active subscribers

### Expected outcome

- Operators know when the system is unhealthy.
- AI cost and performance are measurable.
- Missing newsletters and failed workers are detected quickly.
- Production decisions use evidence.

### Completion criteria

- Metrics are collected.
- Logs are searchable.
- Critical alerts exist.
- Worker and scheduler health are visible.
- AI usage and email delivery can be reviewed over time.

---

## Task 18 — Add real health and readiness checks

**Difficulty:** 5/10  
**Importance:** 9/10  
**Priority:** Launch-critical

### What this task means

Distinguish between:

- **Liveness:** the process is running
- **Readiness:** the application can serve real requests

Readiness should consider:

- Database connectivity
- Required configuration
- Migration status
- Redis availability
- Worker freshness
- Scheduler health where appropriate

### Expected outcome

- Deployment systems know when the application is usable.
- Broken dependencies are detected.
- A running but unusable API is not reported as healthy.

### Completion criteria

- Separate liveness and readiness endpoints exist.
- Readiness fails when critical dependencies are unavailable.
- Containers and deployment systems can use the checks.

---

# Phase 6 — Production infrastructure

## Task 19 — Create complete Docker-based environments

**Difficulty:** 8/10  
**Importance:** 10/10  
**Priority:** Launch-critical

### What this task means

Containerize the full stack, not only PostgreSQL.

The stack should include:

- Frontend
- FastAPI
- Celery workers
- Celery scheduler
- PostgreSQL
- Redis
- Reverse proxy or equivalent production entry point

Development and production configuration should be separated.

### Expected outcome

- The application starts predictably.
- Windows development works through Docker or WSL2.
- Production runs in Linux containers.
- Environment differences are reduced.
- New developers do not manually configure many processes.

### Completion criteria

- Full stack starts through documented commands.
- Services communicate correctly.
- Restart policies and health checks exist.
- Production secrets are not stored in source control.
- Migrations are applied safely.

---

## Task 20 — Add CI/CD and a staging environment

**Difficulty:** 7/10  
**Importance:** 9/10  
**Priority:** Launch-critical

### What this task means

Automatically validate changes and test them in a production-like environment before release.

CI should cover:

- Backend linting and tests
- Frontend linting, tests, and production build
- Database migrations
- Authentication
- Subscription flow
- Celery tasks
- Email idempotency

### Expected outcome

- Broken code is caught before merging.
- Deployments are repeatable.
- Critical flows are tested in staging.
- Releases do not depend on remembered manual commands.

### Completion criteria

- Pull requests run automated checks.
- Failed checks block merging.
- Staging environment exists.
- Deployment is documented and repeatable.
- Migrations are validated before production.

---

## Task 21 — Add secret management and environment separation

**Difficulty:** 5/10  
**Importance:** 10/10  
**Priority:** Launch-critical

### What this task means

Remove unsafe defaults and separate development, testing, staging, and production configuration.

This includes:

- Database credentials
- Redis credentials
- Gemini keys
- Email keys
- Session secrets
- Admin credentials
- Frontend origins
- Monitoring credentials

### Expected outcome

- Production secrets are not committed.
- The application refuses unsafe placeholder secrets in production.
- Development and production configuration cannot accidentally mix.
- Secrets can be rotated.

### Completion criteria

- Safe example configuration exists.
- Placeholder production secrets are rejected.
- Each environment has separate values.
- Secret rotation is documented.

---

## Task 22 — Add database backups and disaster recovery

**Difficulty:** 6/10  
**Importance:** 10/10  
**Priority:** Launch-critical

### What this task means

Protect permanent data against deletion, corruption, failed migrations, and infrastructure failure.

Permanent data includes:

- Users
- Preferences and subscriptions
- Stories and digests
- Newsletter history
- Delivery records

Redis must be treated as temporary queue infrastructure, not the only location of important state.

### Expected outcome

- Production data can be restored.
- A failed migration or infrastructure incident does not permanently destroy the product.
- Recovery is documented rather than improvised.

### Completion criteria

- Automated backups exist.
- Retention is defined.
- Backups are encrypted.
- Restore instructions exist.
- At least one restore test has been performed.
- Migration recovery strategy exists.

---

# Phase 7 — Security, privacy, and trust

## Task 23 — Harden application security

**Difficulty:** 8/10  
**Importance:** 10/10  
**Priority:** Launch-critical

### What this task means

Apply production protections across accounts, APIs, admin functions, and infrastructure.

Include:

- Strong password hashing
- Secure HTTP-only cookies
- HTTPS-only behavior
- CSRF protection
- Rate limiting
- Restricted CORS
- Input validation
- Admin authorization
- Dependency scanning
- Least-privilege database access
- Safe error messages

### Expected outcome

- Customer accounts are reasonably protected.
- Admin operations are isolated.
- Common web attacks are reduced.
- Sensitive information is not exposed.

### Completion criteria

- Login and account operations have appropriate controls.
- State-changing requests are protected.
- Admin routes require admin permissions.
- Production errors do not expose secrets or stack traces.
- Security checks are part of the release process.

---

## Task 24 — Add privacy, data export, and account deletion controls

**Difficulty:** 6/10  
**Importance:** 9/10  
**Priority:** Launch-critical

### What this task means

Give users control over personal data and explain how it is handled.

Users should be able to:

- See relevant stored information
- Export their account data
- Delete their account
- Understand data collection and email use

The product should also have privacy and terms pages appropriate for its launch.

### Expected outcome

- The product feels trustworthy.
- Users can leave without contacting the administrator.
- Personal-data handling is clear.
- The application is better prepared for real users.

### Completion criteria

- Privacy policy exists.
- Terms of service exist.
- Account deletion removes or anonymizes personal data appropriately.
- Data export is available.
- Newsletter consent is recorded.

---

# Phase 8 — AI quality and scalability

## Task 25 — Build a real clustering evaluation dataset

**Difficulty:** 7/10  
**Importance:** 8/10  
**Priority:** High

### What this task means

Evaluate duplicate-story clustering on real news examples instead of only controlled tests.

Include:

- Same event with different wording
- Different announcements from the same company
- Follow-up coverage
- Similar titles about different models
- Old and new related stories
- Union-find chaining
- Single-source stories

Measure:

- Precision
- Recall
- F1 score
- Cluster purity
- False-positive merges
- False-negative splits

### Expected outcome

- Similarity thresholds are supported by evidence.
- Clustering changes can be compared objectively.
- Known failures become regression tests.
- Duplicate reduction improves without incorrectly combining stories.

### Completion criteria

- Labelled dataset exists.
- Current thresholds have measured results.
- False positives and false negatives are reviewed.
- Threshold changes require evaluation.

---

## Task 26 — Add LLM quality evaluation

**Difficulty:** 7/10  
**Importance:** 8/10  
**Priority:** High

### What this task means

Measure whether generated digests and rankings are grounded, accurate, useful, and consistent.

Evaluate:

- Unsupported claims
- Missing important facts
- Incorrect names or numbers
- Source attribution
- Conflicting sources
- Structured-output validity
- Personalization relevance
- Story diversity
- Repetition

### Expected outcome

- Prompt and model changes can be evaluated.
- Hallucination and grounding problems become measurable.
- Quality improves using evidence rather than intuition.

### Completion criteria

- Evaluation cases exist.
- Model and prompt versions are recorded.
- Structured-output failures are measured.
- Quality regressions can be detected.

---

## Task 27 — Persist and reuse embeddings

**Difficulty:** 7/10  
**Importance:** 7/10  
**Priority:** High after launch foundation

### What this task means

Store embeddings so unchanged content is not embedded repeatedly.

Each embedding should be connected to:

- Source item
- Embedding model and version
- Content hash
- Creation time

PostgreSQL with pgvector is a suitable option.

### Expected outcome

- Repeated runs are faster.
- Embedding cost is reduced.
- Similarity decisions are easier to inspect.
- Historical semantic retrieval becomes possible.

### Completion criteria

- Unchanged content reuses stored embeddings.
- Embeddings regenerate when content or model changes.
- Embedding metadata is traceable.
- Clustering still behaves correctly.

---

## Task 28 — Optimize retrieval and personalization at scale

**Difficulty:** 8/10  
**Importance:** 6/10 initially  
**Priority:** Later

### What this task means

Improve efficiency only when measured usage reveals real bottlenecks.

Potential areas:

- Vector candidate retrieval
- Avoiding all-pairs comparisons
- Caching common digests
- Batching user ranking
- Reducing unnecessary LLM calls
- Separating heavy and light queues
- Database indexing and connection pooling

### Expected outcome

- Processing stays affordable at higher volume.
- Queue delays remain controlled.
- Cost per subscriber is understandable.
- The system grows without replacing its core architecture.

### Completion criteria

- Bottlenecks are measured first.
- Optimizations address measured issues.
- Performance or cost improves without reducing quality.

---

# Phase 9 — Analytics, billing, and growth

## Task 29 — Add product analytics and user feedback

**Difficulty:** 6/10  
**Importance:** 7/10  
**Priority:** After initial beta

### What this task means

Measure whether users understand and value the product.

Track:

- Homepage conversion
- Registration completion
- Onboarding completion
- Subscription activation
- Newsletter opens
- Story clicks
- Unsubscribe rate
- Weekly retention
- Interest changes
- Newsletter feedback

### Expected outcome

- Product decisions use real behavior.
- Weak onboarding steps can be identified.
- Ranking and newsletter quality can improve.
- Retention becomes measurable.

### Completion criteria

- Core product funnel is tracked.
- Newsletter engagement is measurable.
- Feedback is stored.
- Analytics respects privacy choices.

---

## Task 30 — Add billing after validating the free beta

**Difficulty:** 8/10  
**Importance:** 8/10 for a paid product  
**Priority:** Later

### What this task means

Add paid subscriptions only after proving that users complete onboarding, open newsletters, and continue using the product.

Billing should represent:

- Plans
- Paid subscriptions
- Trials
- Payment status
- Invoices
- Failed payments
- Cancellation
- Verified payment events

### Expected outcome

- The product can charge users reliably.
- Payment status controls paid access.
- Failed payments can be recovered.
- Billing history is auditable.

### Completion criteria

- Payment-provider integration works.
- Payment events are verified.
- Subscription state updates correctly.
- Failed-payment behavior is defined.
- Users can cancel paid plans.

---

# Recommended implementation order

## Stage 1 — Customer-facing beta

1. Define product scope
2. Redesign the multi-user database
3. Build authentication
4. Build the homepage
5. Build onboarding
6. Build account and subscription settings
7. Separate global and per-user pipelines

## Stage 2 — Reliable automated delivery

8. Migrate to Celery and Redis
9. Add recurring scheduling
10. Make generation and delivery idempotent
11. Add timeouts, retries, and rate-limit handling
12. Add failed-task recovery
13. Integrate a production email provider
14. Add verification and unsubscribe handling

## Stage 3 — Production launch foundation

15. Convert the dashboard into a private admin console
16. Build the complete Docker stack
17. Add CI/CD and staging
18. Add secret management
19. Harden security
20. Add health checks
21. Add monitoring and alerts
22. Add backups and disaster recovery
23. Add privacy and account controls

## Stage 4 — Quality, scale, and commercial features

24. Build clustering evaluation
25. Build LLM quality evaluation
26. Persist embeddings
27. Optimize at scale
28. Add product analytics
29. Add billing after validating the beta

---

# Definition of a production-ready beta

The product may be considered ready for a serious public beta when:

- Users can register and verify their email.
- Users can select interests and subscribe.
- Weekly personalized newsletters are generated automatically.
- Global processing is independent of subscriber count.
- Background work runs through Celery and Redis.
- Retries cannot create duplicate newsletters or emails.
- Email delivery uses a production provider.
- Users can pause, unsubscribe, and delete their account.
- The old dashboard is private and used for operations.
- The full application is containerized.
- CI checks run before deployment.
- Production secrets are managed safely.
- Monitoring and alerts exist.
- Database backups are automated and tested.
- Critical user and delivery flows have automated tests.

---

# Explicit non-goals for the first public beta

The first beta does not need:

- Daily newsletters
- Monthly newsletters
- Mobile applications
- Team accounts
- Multiple languages
- Complex recommendation controls
- Social feeds
- Real-time breaking-news alerts
- Advanced trend reports
- Paid billing on day one
- Large-scale vector optimization before usage requires it

These features must not delay the core weekly newsletter product.

---

# Final target

After this roadmap is implemented, the application should operate as:

> A clean, customer-facing, personalized AI-news newsletter platform with reliable automated processing, safe email delivery, private operational controls, measurable AI quality, and production-grade infrastructure.
