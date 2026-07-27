# FortniteBR Community Sample Collector — Prototype v0.1

A small, external, read-only feasibility prototype that requests a strictly bounded sample of public posts and comments from `r/FortniteBR` through Reddit's approved Data API.

> **Approval gate:** Do not run this project until Reddit has explicitly approved the stated Data API use case and issued or confirmed the applicable credentials and OAuth flow.

This project is not affiliated with, endorsed by, or sponsored by Reddit, Epic Games, or Fortnite.

## Current purpose

The first version performs collection only. It exports a small local JSON sample for private human review to test whether public Fortnite discussions add useful context around official events.

It does **not** perform automated sentiment analysis, LLM analysis, model training, public distribution, or commercial delivery. Any future phase involving automated summarization, third-party AI processing, broader subreddit coverage, recurring production collection, or commercial use requires a separate compliance review and any additional written approval required by Reddit.

## Exact approved scope requested

- Community: public `r/FortniteBR` only.
- Execution: manual feasibility run.
- Listings: at most 10 `Hot` posts and 10 `New` posts.
- Selection: at most 5 posts.
- Comments: at most 30 comments per selected post.
- Recency: at most 7 days.
- Reddit data requests: at most 7 per run (2 listings + 5 comment endpoints), excluding the OAuth token request.
- Actions: read-only; no posting, commenting, voting, messaging, moderation, or private data access.

These ceilings are enforced in code and cannot be increased through command-line arguments.

## Data minimization

The exported JSON:

- omits usernames and profile URLs;
- omits comment IDs, parent IDs, and direct comment permalinks;
- skips deleted and removed comment bodies;
- excludes NSFW posts;
- truncates post and comment text to short excerpts;
- retains the original thread permalink for attribution and human verification;
- auto-purges JSON files in `output/` after 24 hours on the next run.

No age, identity, or sensitive characteristic is inferred. Reddit discussion is not treated as representative of all Fortnite players.

## What the code does

1. Uses OAuth credentials approved for this use case.
2. Reads bounded `Hot` and `New` listings from public `r/FortniteBR`.
3. Deduplicates overlapping posts.
4. Applies deterministic relevance and recency scoring.
5. Reads a bounded comment sample for selected threads.
6. Writes a minimized JSON file for local human review.
7. Purges stale local JSON output.

## What the code does not do

- No scraping, browser automation, archived mirrors, or unauthenticated `.json` workaround.
- No attempt to bypass approval, OAuth, rate limits, or access controls.
- No LLM call and no AI/ML/NLP model training or improvement.
- No user profiling, re-identification, cross-platform matching, or age inference.
- No storage of Reddit usernames.
- No public or commercial redistribution of Reddit data.
- No Notion, Google Sheets, Discord, or other third-party write integration.
- No scheduling or unattended recurring execution.

## Requirements

- Python 3.10 or newer.
- Explicit Reddit Data API approval for this exact use case.
- Credentials and OAuth grant confirmed by Reddit.
- A unique, descriptive `User-Agent` with a Reddit contact username.

The prototype currently implements application-only OAuth using `client_credentials`. Reddit's approval response is the source of truth; update the authentication implementation if Reddit specifies a different approved flow.

## Setup

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

If PowerShell blocks activation for the current session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Linux or macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Populate `.env` locally only:

```text
REDDIT_CLIENT_ID=replace_me
REDDIT_CLIENT_SECRET=replace_me
REDDIT_USER_AGENT=windows:qa.maeen.fortnitebr:v0.1 (by /u/replace_me)
```

Never commit or share `.env`, access tokens, or client secrets.

## Run

```powershell
.\.venv\Scripts\python.exe .\reddit_collector.py
```

Optional arguments may only reduce or vary collection within the hard ceilings:

```powershell
.\.venv\Scripts\python.exe .\reddit_collector.py --hot 10 --new 10 --select 5 --comments 30 --max-age-days 7 --comment-sort top
```

Output:

```text
output/fortnitebr_sample.json
```

Delete the file after review. The next run automatically removes JSON outputs older than 24 hours.

## Tests

Tests are local and do not connect to Reddit:

```bash
python -m unittest discover -s tests -v
```

They verify deduplication, deterministic selection, identifier minimization, deleted-content handling, hard ceilings, and retention cleanup.

## Governance documents

- [`PRIVACY.md`](PRIVACY.md) — data handling and retention.
- [`COMPLIANCE.md`](COMPLIANCE.md) — operational policy controls.
- [`REDDIT_ACCESS_REQUEST.md`](REDDIT_ACCESS_REQUEST.md) — narrow request summary for reviewer transparency.
- [`APPLICATION_FORM_ANSWERS.md`](APPLICATION_FORM_ANSWERS.md) — policy-aligned draft answers for the access form.
- [`NOTICE.md`](NOTICE.md) — trademark and affiliation notice.

## Status

Prototype only. A successful approval and live sample are still required before evaluating community-analysis value.
