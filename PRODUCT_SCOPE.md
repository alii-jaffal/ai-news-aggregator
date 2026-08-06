# AI News Aggregator V1 Product Scope

## Purpose

This document is the locked source of truth for the first customer-facing version of AI News Aggregator.

Use it to judge future work, especially roadmap items such as authentication, multi-user data modeling, personalization, and the public product experience. If a future task conflicts with this document, this document wins unless the team intentionally revises the scope.

## Product Promise

> A weekly AI news briefing for AI professionals that removes duplicate coverage and surfaces the stories that matter.

## Target User

The first version is for AI professionals, not for a broad consumer audience.

This includes:

- software engineers building AI features
- AI and ML engineers
- product managers working on AI products
- founders and technical operators in AI-focused teams
- similar job-based readers who want high-signal AI updates

These readers usually want useful product, model, tooling, and ecosystem updates without reading the same story across many sources.

## Locked V1 Decisions

- Frequency: weekly only
- Language: English only
- Newsletter size: 7 stories per issue
- Access model: free private beta
- Audience: AI professionals
- Core differentiation: combine duplicate coverage into one canonical story, then rank stories for the reader
- Personalization inputs: interests and expertise level
- Delivery model: global scraping, enrichment, clustering, and digest generation happen once; user-level personalization happens later in ranking and delivery

## What Personalization Means In V1

Personalization in v1 is intentionally narrow.

- Interests influence which stories rank higher.
- Expertise level influences ranking and newsletter tone.
- The expensive content pipeline remains global and shared.

V1 does not require advanced preference tuning, complex source controls, or separate per-user content processing pipelines before ranking.

## Success Definition

The first version succeeds if a private-beta user receives one concise weekly issue that:

- feels relevant to their AI interests
- avoids repeated coverage of the same story
- highlights a small number of high-signal stories
- stays readable for an AI-professional audience

## Deferred Features

The following are explicitly out of scope for v1:

- daily newsletters
- mobile app
- billing or paid tiers
- team accounts
- broad consumer positioning
- multi-language support
- complex preference tuning beyond interests and expertise level
- public self-serve signup at scale

## Guidance For Later Tasks

This scope should guide later implementation decisions.

- Task 3 should build real user accounts for private-beta subscribers, not a mass-market signup funnel.
- Task 6 should replace the single active profile with a multi-user model that supports subscriber preferences and history.
- Task 7 should keep global processing shared and move personalization to the user-specific ranking and delivery path.
- Task 12 and later product work should optimize for AI professionals rather than a general audience.

## Current-State Note

As of August 6, 2026, the repository still contains an internal admin dashboard and a pipeline-oriented workflow. This document defines the intended first public product scope, not a claim that every part of that product already exists.
