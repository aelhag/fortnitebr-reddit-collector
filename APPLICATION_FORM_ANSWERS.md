# Suggested Reddit Data Access Request Answers

Use these answers only if they accurately describe the submitted code and intended operation. Replace `<YOUR_REDDIT_USERNAME>` before submission.

## Reddit account name

```text
<YOUR_REDDIT_USERNAME>
```

## What benefit/purpose will the bot/app have for Redditors?

```text
The app is a small, read-only technical feasibility prototype intended to reduce misunderstanding of public Fortnite community discussions by non-players, particularly parents.

It will retrieve a strictly limited sample of public r/FortniteBR threads for private human review. The review will test whether recurring community concerns, technical problems, and gaming terminology can be explained accurately while preserving attribution and linking back to the original Reddit threads.

The current prototype does not interact with Reddit users. It does not post, comment, vote, send messages, moderate communities, profile users, infer ages or sensitive characteristics, or publish a dataset. Any benefit is indirect: preserving context, avoiding misleading representations of Reddit discussions, and directing reviewers to the original public threads.
```

## Provide a detailed description of what the Bot/App will be doing on the Reddit platform

```text
This is a non-production, external, read-only feasibility prototype.

After explicit Reddit Data API approval, it will perform a manual run against public r/FortniteBR content only. The code enforces the following maximum scope per run:

- 10 Hot posts.
- 10 New posts.
- 5 selected threads after deduplication and deterministic relevance filtering.
- 30 comments per selected thread.
- Posts no older than 7 days.
- A maximum of 7 Reddit data endpoint requests per run, excluding the OAuth token request.

The current version performs collection only and exports a minimized local JSON file for private human review. It does not run automated sentiment analysis, call an LLM, train or improve an AI/ML/NLP model, or send Reddit content to a third-party service.

The exported file omits Reddit usernames, profile URLs, comment IDs, parent IDs, and direct comment permalinks. Deleted and removed comments are skipped, NSFW posts are excluded, and text is limited to short excerpts. Original thread links are retained for attribution and verification.

JSON output is temporary. The code automatically purges JSON files older than 24 hours on the next run, and the operator will delete the current output after review.

The app will not post, comment, vote, message users, moderate communities, access private content, infer user age, infer sensitive characteristics, re-identify users, or combine Reddit data with off-platform identifiers.

This request does not include automated summarization, broader subreddit coverage, recurring production monitoring, public distribution, or commercial use. Those activities will not begin without a separate compliance review and any additional explicit written approval required by Reddit.
```

## What is missing from Devvit that prevents building on that platform?

```text
The prototype is an external local collector rather than a subreddit-installed experience or moderation tool.

I am not a moderator of r/FortniteBR and cannot install a Devvit application in that community. The test needs approved read-only access to a small sample of public posts and comments from r/FortniteBR and must export a minimized local JSON file for private human review.

The app does not need Reddit UI components, in-community commands, moderation actions, user interaction, or posting functionality. Devvit's installation-scoped model therefore does not support this specific external feasibility test for a community where I do not have installation authority.
```

## Provide a link to source code or platform that will access the API

```text
https://github.com/aelhag/fortnitebr-reddit-collector
```

## What subreddits do you intend to use the bot/app in?

```text
r/FortniteBR only.

The current code hard-codes this subreddit and does not allow the operator to select another subreddit through command-line arguments.
```

## If applicable, what username will you be operating this Bot/App under?

```text
Not applicable. The prototype is read-only and will not operate a visible bot account, post, comment, vote, send messages, or perform moderation actions.
```

## Optional attachment note

```text
The attached ZIP matches the public GitHub repository. It contains source code, local tests, an environment-variable template without credentials, and privacy/compliance documentation. It does not contain an .env file, access token, client secret, collected Reddit data, virtual environment, or cache files.
```
