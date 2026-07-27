# Data API Access Request Summary

## Use case

A non-production, read-only technical feasibility prototype that retrieves a small sample of public posts and comments from `r/FortniteBR` for private human review.

The test asks whether public community discussions add useful context to officially announced Fortnite events. The current version performs collection only. It does not run automated sentiment analysis, call an LLM, train a model, publish results, or provide a commercial service.

## Why Devvit is not sufficient

The workflow is an external local collector, not a subreddit-installed experience or moderation tool. The developer is not a moderator of `r/FortniteBR` and cannot install a Devvit application there. The required output is a small local JSON sample for private human review.

## Requested scope

- Subreddit: `r/FortniteBR` only.
- Public content only.
- Manual run.
- Read-only.
- Up to 10 Hot posts and 10 New posts.
- Up to 5 selected threads.
- Up to 30 comments per selected thread.
- Up to 7 Reddit data endpoint requests per run, excluding OAuth.

## Data handling

- No usernames or profile URLs exported.
- No comment IDs or direct comment links exported.
- No private content.
- No age or sensitive-characteristic inference.
- No user profiling or re-identification.
- Deleted and removed comments skipped.
- Local output retained for less than 24 hours and deleted after review.
- Original thread links retained for attribution and verification.

## Future boundaries

Automated summarization, sending Reddit content to an AI provider, broader subreddit coverage, recurring production monitoring, public distribution, or commercial use are not part of this request and will not begin without a separate compliance review and any additional explicit written approval required by Reddit.
