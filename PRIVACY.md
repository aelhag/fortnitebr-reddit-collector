# Privacy and Data Handling

Last updated: 2026-07-27

## Scope

This prototype processes a bounded sample of public posts and comments from `r/FortniteBR` only after explicit Reddit Data API approval.

## Data collected

The local output may contain:

- post title and a bounded body excerpt;
- original thread permalink;
- public timestamps, flair, and time-specific engagement snapshots;
- bounded comment text excerpts, timestamps, depth, and score snapshots.

## Data intentionally not collected or exported

- Reddit usernames or profile URLs;
- private messages, private communities, or private profile data;
- comment IDs, parent IDs, or direct comment permalinks;
- inferred age, identity, or sensitive characteristics;
- deleted or removed comment bodies;
- NSFW posts.

## Purpose

Data is used only for a private, manual technical feasibility review. The current code does not call an LLM, train or improve a model, profile users, publish a dataset, or provide a commercial service.

## Retention

JSON outputs are local and temporary. The application automatically purges JSON files in `output/` that are older than 24 hours when it next runs. The operator should delete the current output immediately after review and must not copy it into a longer-lived system without a separately approved retention basis.

## Sharing

The current prototype does not transmit collected Reddit content to Notion, Google Sheets, an AI provider, analytics service, or another third party. The output is not publicly distributed.

## Security

OAuth credentials are stored only in a local `.env` file excluded by `.gitignore`. Credentials, access tokens, and raw output must not be committed to source control or attached to support tickets.

## Deletion and termination

If Reddit withdraws approval or requests deletion, collection stops and all stored Reddit content must be deleted. Content no longer required for the approved use case must be deleted immediately.

## Contact

Use the repository's GitHub Issues page for privacy or deletion questions. Do not include Reddit usernames, access tokens, or private information in an issue.
