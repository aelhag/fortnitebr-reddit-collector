# Reddit Data API Compliance Controls

This document describes controls implemented for the feasibility prototype. It is not legal advice and does not replace Reddit's approval or terms.

## Approval and authentication

- Do not run before explicit Reddit Data API approval.
- Use only the credentials, OAuth flow, subreddit scope, and actions Reddit approves.
- Do not use unauthenticated JSON endpoints, mirrors, archives, browser automation, or scraping as a fallback.
- Use a unique descriptive `User-Agent` and do not mask OAuth identity.

## Fixed scope

- Public `r/FortniteBR` only.
- Manual execution only.
- Read-only endpoints only.
- No private content or user communications.
- No posting, commenting, voting, messaging, or moderation.

## Hard ceilings per run

- 10 Hot posts.
- 10 New posts.
- 5 selected posts.
- 30 comments per selected post.
- 7-day maximum age.
- 7 Reddit data endpoint requests maximum, excluding OAuth.

The CLI can reduce these values but cannot increase them.

## Data minimization

- No usernames or profile URLs in output.
- No comment IDs, parent IDs, or direct comment permalinks in output.
- Deleted and removed comments are skipped.
- NSFW posts are excluded.
- Text is truncated to bounded excerpts.
- Original thread links are kept for attribution and verification.

## Retention

- Output is local only.
- JSON outputs older than 24 hours are automatically purged on the next run.
- The operator must delete the current sample after review.
- No long-term archive, dataset release, or resale.

## AI and analytics

Current version:

- does not call an LLM;
- does not train, fine-tune, improve, or evaluate an AI/ML/NLP model with Reddit data;
- does not send Reddit content to a third-party AI service;
- does not infer age or sensitive characteristics;
- does not profile or re-identify users.

Any future automated summarization or external AI processing is out of scope and requires a new compliance review and any additional written Reddit approval.

## Commercial use

The current prototype is non-production and non-commercial. No Reddit data will be used to power, augment, or enhance a commercial product without Reddit's explicit written approval and any required agreement.

## Rate limits and safe failure

- Observe `X-Ratelimit-*` response headers.
- Stop on `401`, `403`, or `429` and investigate approved scope or reset timing.
- Do not rotate accounts, create duplicate apps, or submit duplicate requests to bypass limits.
- Retry only transient server errors with bounded exponential backoff.

## Reviewer checklist before each run

- [ ] Explicit approval received for this exact use case.
- [ ] OAuth flow and credentials confirmed by Reddit.
- [ ] Only `r/FortniteBR` is accessed.
- [ ] No code changes expanded collection, retention, or downstream sharing.
- [ ] `.env` is untracked and secrets are not in logs.
- [ ] Prior JSON output has been deleted or is within the 24-hour window.
- [ ] The planned run remains manual and non-commercial.
