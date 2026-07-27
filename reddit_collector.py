#!/usr/bin/env python3
"""Bounded, read-only community sample collector for r/FortniteBR.

This disposable feasibility prototype:
- requires explicit Reddit Data API approval before use;
- reads only public r/FortniteBR posts and comments;
- enforces hard collection ceilings;
- removes usernames and comment-level identifiers from exported JSON;
- automatically purges stale JSON outputs;
- does not call an LLM, train a model, publish, vote, message, or moderate.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE = "https://oauth.reddit.com"
APPROVED_SUBREDDIT = "FortniteBR"
OUTPUT_DIR = Path("output")
DEFAULT_OUTPUT = OUTPUT_DIR / "fortnitebr_sample.json"
RETENTION_HOURS = 24

# Hard ceilings intentionally match the narrow feasibility request.
MAX_HOT_POSTS = 10
MAX_NEW_POSTS = 10
MAX_SELECTED_POSTS = 5
MAX_COMMENTS_PER_POST = 30
MAX_AGE_DAYS = 7
MAX_COMMENT_DEPTH = 3
MAX_POST_EXCERPT_CHARS = 800
MAX_COMMENT_EXCERPT_CHARS = 800

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "safety_account_chat": (
        "parental", "parent", "voice chat", "text chat", "chat", "account",
        "scam", "hack", "hacked", "ban", "banned", "age", "report",
        "discord", "lfg", "stranger", "privacy",
    ),
    "purchase_fomo": (
        "item shop", "shop", "v-bucks", "vbucks", "crew", "bundle", "price",
        "refund", "limited", "exclusive", "skin", "cosmetic",
    ),
    "event_update": (
        "event", "update", "season", "chapter", "live event", "downtime",
        "maintenance", "collab", "collaboration", "quest", "reward",
    ),
    "technical_issue": (
        "bug", "broken", "issue", "glitch", "crash", "lag", "server",
        "matchmaking", "missing", "not working", "error",
    ),
    "competitive": (
        "ranked", "tournament", "fncs", "competitive", "scrim", "qualifier",
        "prize", "cash cup",
    ),
}

LOW_INFORMATION_FLAIRS = {"humor", "meme", "media", "artistic"}
LOW_INFORMATION_TITLE_PATTERNS = (
    re.compile(r"^rate my", re.I),
    re.compile(r"^what skin", re.I),
    re.compile(r"^which skin", re.I),
)


class CollectorError(RuntimeError):
    """Expected operational failure with a user-actionable message."""


@dataclass(frozen=True)
class Config:
    hot_limit: int
    new_limit: int
    select_limit: int
    comments_limit: int
    max_age_days: int
    comment_sort: str
    output_path: Path
    request_timeout: int
    pause_seconds: float


def utc_iso(epoch_seconds: float | int | None) -> str | None:
    if epoch_seconds is None:
        return None
    return datetime.fromtimestamp(float(epoch_seconds), tz=timezone.utc).isoformat()


def normalize_text(value: Any, max_chars: int | None = None) -> str:
    if not isinstance(value, str):
        return ""
    text = html.unescape(value).replace("\x00", "").strip()
    text = re.sub(r"\r\n?", "\n", text)
    if max_chars and len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "…"
    return text


def purge_stale_outputs(directory: Path, retention_hours: int = RETENTION_HOURS) -> int:
    """Delete JSON outputs older than the fixed local retention window."""
    if retention_hours <= 0:
        raise ValueError("retention_hours must be greater than zero")
    if not directory.exists():
        return 0

    cutoff = time.time() - retention_hours * 3600
    deleted = 0
    for path in directory.glob("*.json"):
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                deleted += 1
        except OSError as exc:
            raise CollectorError(f"Could not purge stale output {path}: {exc}") from exc
    return deleted


def build_session(user_agent: str) -> requests.Session:
    retries = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})
    session.mount("https://", adapter)
    return session


def get_access_token(
    session: requests.Session,
    client_id: str,
    client_secret: str,
    timeout: int,
) -> tuple[str, int]:
    try:
        response = session.post(
            TOKEN_URL,
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise CollectorError(f"OAuth token request failed: {exc}") from exc

    if response.status_code in {401, 403}:
        raise CollectorError(
            "Reddit rejected the OAuth credentials or the app lacks explicit Data API "
            f"approval (HTTP {response.status_code}). Do not route around the approval gate."
        )
    if not response.ok:
        raise CollectorError(
            f"OAuth token request failed with HTTP {response.status_code}: "
            f"{normalize_text(response.text, 500)}"
        )

    payload = response.json()
    token = payload.get("access_token")
    expires_in = int(payload.get("expires_in", 3600))
    if not token:
        raise CollectorError("OAuth response did not include access_token.")
    return str(token), expires_in


def reddit_get(
    session: requests.Session,
    token: str,
    path: str,
    params: dict[str, Any],
    timeout: int,
) -> tuple[Any, dict[str, str]]:
    headers = {"Authorization": f"bearer {token}"}
    final_params = {"raw_json": 1, **params}
    try:
        response = session.get(
            f"{API_BASE}{path}", headers=headers, params=final_params, timeout=timeout
        )
    except requests.RequestException as exc:
        raise CollectorError(f"Reddit API request failed for {path}: {exc}") from exc

    rate_headers = {
        key: response.headers.get(key, "")
        for key in ("x-ratelimit-used", "x-ratelimit-remaining", "x-ratelimit-reset")
    }

    if response.status_code == 429:
        raise CollectorError(
            "Reddit API rate limit reached. Retry only after the reset window. "
            f"Headers: {rate_headers}"
        )
    if response.status_code in {401, 403}:
        raise CollectorError(
            f"Reddit API denied {path} (HTTP {response.status_code}). "
            "Stop and verify approved scope and credentials; do not use an alternate scraper."
        )
    if not response.ok:
        raise CollectorError(
            f"Reddit API request {path} failed with HTTP {response.status_code}: "
            f"{normalize_text(response.text, 500)}"
        )

    try:
        return response.json(), rate_headers
    except ValueError as exc:
        raise CollectorError(f"Reddit returned non-JSON content for {path}.") from exc


def extract_listing_posts(payload: Any, listing_name: str) -> list[dict[str, Any]]:
    try:
        children = payload["data"]["children"]
    except (TypeError, KeyError) as exc:
        raise CollectorError(f"Unexpected Reddit listing response for {listing_name}.") from exc

    posts: list[dict[str, Any]] = []
    for child in children:
        if child.get("kind") != "t3":
            continue
        data = child.get("data", {})
        post_id = str(data.get("id", "")).strip()
        if not post_id:
            continue
        posts.append(
            {
                "post_id": post_id,
                "title": normalize_text(data.get("title"), 500),
                "selftext": normalize_text(data.get("selftext"), MAX_POST_EXCERPT_CHARS),
                "permalink": f"https://www.reddit.com{data.get('permalink', '')}",
                "created_utc": data.get("created_utc"),
                "score": int(data.get("score") or 0),
                "upvote_ratio": data.get("upvote_ratio"),
                "num_comments": int(data.get("num_comments") or 0),
                "flair": normalize_text(data.get("link_flair_text"), 100),
                "over_18": bool(data.get("over_18")),
                "spoiler": bool(data.get("spoiler")),
                "stickied": bool(data.get("stickied")),
                "locked": bool(data.get("locked")),
                "listings": [listing_name],
            }
        )
    return posts


def merge_posts(*post_lists: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for posts in post_lists:
        for post in posts:
            post_id = post["post_id"]
            if post_id not in merged:
                merged[post_id] = dict(post)
            else:
                existing = merged[post_id]
                existing["listings"] = sorted(
                    set(existing.get("listings", [])) | set(post.get("listings", []))
                )
                existing["score"] = max(int(existing.get("score", 0)), int(post.get("score", 0)))
                existing["num_comments"] = max(
                    int(existing.get("num_comments", 0)), int(post.get("num_comments", 0))
                )
    return list(merged.values())


def detect_topics(post: dict[str, Any]) -> list[str]:
    haystack = f"{post.get('title', '')}\n{post.get('selftext', '')}".lower()
    return [
        topic
        for topic, keywords in TOPIC_KEYWORDS.items()
        if any(keyword in haystack for keyword in keywords)
    ]


def is_low_information(post: dict[str, Any]) -> bool:
    flair = str(post.get("flair", "")).strip().lower()
    title = str(post.get("title", "")).strip()
    if flair in LOW_INFORMATION_FLAIRS and post.get("num_comments", 0) < 40:
        return True
    return any(pattern.search(title) for pattern in LOW_INFORMATION_TITLE_PATTERNS)


def selection_score(post: dict[str, Any], now_epoch: float) -> float:
    age_hours = max(0.0, (now_epoch - float(post.get("created_utc") or now_epoch)) / 3600)
    recency = max(0.0, 1.0 - age_hours / (MAX_AGE_DAYS * 24)) * 3.0
    discussion = math.log1p(max(0, int(post.get("num_comments", 0)))) * 1.8
    community_score = math.log1p(max(0, int(post.get("score", 0)))) * 0.6
    topic_bonus = len(detect_topics(post)) * 1.4
    body_bonus = 1.0 if len(str(post.get("selftext", ""))) >= 120 else 0.0
    listing_bonus = 0.8 if len(post.get("listings", [])) > 1 else 0.0
    pinned_penalty = 2.0 if post.get("stickied") else 0.0
    low_info_penalty = 3.5 if is_low_information(post) else 0.0
    return round(
        recency + discussion + community_score + topic_bonus + body_bonus
        + listing_bonus - pinned_penalty - low_info_penalty,
        3,
    )


def select_posts(
    posts: list[dict[str, Any]],
    limit: int,
    max_age_days: int,
    now_epoch: float | None = None,
) -> list[dict[str, Any]]:
    now_epoch = now_epoch or time.time()
    cutoff = now_epoch - max_age_days * 86400
    eligible = [
        p for p in posts
        if float(p.get("created_utc") or 0) >= cutoff
        and not p.get("over_18")
        and p.get("title")
    ]
    for post in eligible:
        post["matched_topics"] = detect_topics(post)
        post["selection_score"] = selection_score(post, now_epoch)
    eligible.sort(
        key=lambda p: (
            p["selection_score"],
            int(p.get("num_comments", 0)),
            float(p.get("created_utc") or 0),
        ),
        reverse=True,
    )
    return eligible[:limit]


def flatten_comments(
    children: list[dict[str, Any]],
    max_comments: int,
    max_depth: int = MAX_COMMENT_DEPTH,
) -> tuple[list[dict[str, Any]], int]:
    """Flatten a bounded tree without usernames or comment-level identifiers."""
    output: list[dict[str, Any]] = []
    skipped_more = 0

    def walk(nodes: list[dict[str, Any]], depth: int) -> None:
        nonlocal skipped_more
        if depth > max_depth or len(output) >= max_comments:
            return
        for node in nodes:
            if len(output) >= max_comments:
                return
            kind = node.get("kind")
            if kind == "more":
                skipped_more += len(node.get("data", {}).get("children", []) or [])
                continue
            if kind != "t1":
                continue
            data = node.get("data", {})
            body = normalize_text(data.get("body"), MAX_COMMENT_EXCERPT_CHARS)
            if body in {"", "[deleted]", "[removed]"}:
                continue
            output.append(
                {
                    "depth": int(data.get("depth") or depth),
                    "created_utc": utc_iso(data.get("created_utc")),
                    "score_snapshot": int(data.get("score") or 0),
                    "body_excerpt": body,
                }
            )
            replies = data.get("replies")
            if isinstance(replies, dict):
                nested = replies.get("data", {}).get("children", [])
                if isinstance(nested, list):
                    walk(nested, depth + 1)

    walk(children, 0)
    return output, skipped_more


def parse_comments_payload(payload: Any, max_comments: int) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(payload, list) or len(payload) < 2:
        raise CollectorError("Unexpected Reddit comments response.")
    try:
        children = payload[1]["data"]["children"]
    except (TypeError, KeyError) as exc:
        raise CollectorError("Unexpected Reddit comment tree structure.") from exc
    return flatten_comments(children, max_comments=max_comments)


def safe_public_post(post: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": post["title"],
        "body_excerpt": post["selftext"],
        "thread_permalink": post["permalink"],
        "created_utc": utc_iso(post["created_utc"]),
        "flair": post["flair"] or None,
        "score_snapshot": post["score"],
        "upvote_ratio_snapshot": post["upvote_ratio"],
        "comment_count_snapshot": post["num_comments"],
        "source_listings": post["listings"],
        "matched_topics": post["matched_topics"],
        "selection_score": post["selection_score"],
        "spoiler": post["spoiler"],
        "locked": post["locked"],
    }


def collect(config: Config) -> dict[str, Any]:
    client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    user_agent = os.getenv("REDDIT_USER_AGENT", "").strip()

    missing = [
        name for name, value in (
            ("REDDIT_CLIENT_ID", client_id),
            ("REDDIT_CLIENT_SECRET", client_secret),
            ("REDDIT_USER_AGENT", user_agent),
        ) if not value
    ]
    if missing:
        raise CollectorError("Missing required environment variables: " + ", ".join(missing))
    if "replace_me" in user_agent.lower() or "/u/" not in user_agent:
        raise CollectorError(
            "REDDIT_USER_AGENT must identify the platform, app, version, and contact username."
        )

    session = build_session(user_agent)
    token, token_expires = get_access_token(
        session, client_id, client_secret, config.request_timeout
    )

    rate_limit_observations: list[dict[str, str]] = []
    hot_payload, rate = reddit_get(
        session, token, f"/r/{APPROVED_SUBREDDIT}/hot",
        {"limit": config.hot_limit}, config.request_timeout,
    )
    rate_limit_observations.append({"request": "hot", **rate})
    time.sleep(config.pause_seconds)

    new_payload, rate = reddit_get(
        session, token, f"/r/{APPROVED_SUBREDDIT}/new",
        {"limit": config.new_limit}, config.request_timeout,
    )
    rate_limit_observations.append({"request": "new", **rate})

    merged = merge_posts(
        extract_listing_posts(hot_payload, "hot"),
        extract_listing_posts(new_payload, "new"),
    )
    selected = select_posts(merged, config.select_limit, config.max_age_days)

    exported_posts: list[dict[str, Any]] = []
    for index, post in enumerate(selected):
        if index > 0:
            time.sleep(config.pause_seconds)
        comments_payload, rate = reddit_get(
            session, token, f"/comments/{post['post_id']}",
            {
                "limit": config.comments_limit,
                "depth": MAX_COMMENT_DEPTH,
                "sort": config.comment_sort,
            },
            config.request_timeout,
        )
        rate_limit_observations.append({"request": "comments", **rate})
        comments, skipped_more = parse_comments_payload(
            comments_payload, max_comments=config.comments_limit
        )
        public_post = safe_public_post(post)
        public_post["comments_sample"] = comments
        public_post["comments_read_actual"] = len(comments)
        public_post["unexpanded_comment_ids_count"] = skipped_more
        exported_posts.append(public_post)

    generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": "0.2",
        "generated_at_utc": generated_at,
        "source": {
            "platform": "Reddit Data API",
            "subreddit": APPROVED_SUBREDDIT,
            "community_url": f"https://www.reddit.com/r/{APPROVED_SUBREDDIT}/",
            "authentication": "OAuth client_credentials",
            "read_only": True,
            "explicit_approval_required": True,
        },
        "collection_policy": {
            "hot_requested": config.hot_limit,
            "new_requested": config.new_limit,
            "unique_posts_seen": len(merged),
            "selected_posts": len(exported_posts),
            "max_age_days": config.max_age_days,
            "comments_limit_per_post": config.comments_limit,
            "comment_sort": config.comment_sort,
            "maximum_api_data_requests_per_run": 2 + config.select_limit,
            "authors_stored": False,
            "comment_identifiers_stored": False,
            "nsfw_excluded": True,
            "local_raw_retention_hours": RETENTION_HOURS,
            "not_for_model_training": True,
            "not_for_commercial_use_without_written_approval": True,
        },
        "oauth": {"token_expires_in_seconds": token_expires},
        "rate_limit_observations": rate_limit_observations,
        "posts": exported_posts,
    }


def bounded_int(maximum: int):
    def parse(value: str) -> int:
        parsed = int(value)
        if not 1 <= parsed <= maximum:
            raise argparse.ArgumentTypeError(f"must be between 1 and {maximum}")
        return parsed
    return parse


def parse_args(argv: list[str] | None = None) -> Config:
    parser = argparse.ArgumentParser(
        description=(
            "Collect a strictly bounded, de-identified sample from public r/FortniteBR "
            "after explicit Reddit Data API approval."
        )
    )
    parser.add_argument("--hot", dest="hot_limit", type=bounded_int(MAX_HOT_POSTS), default=10)
    parser.add_argument("--new", dest="new_limit", type=bounded_int(MAX_NEW_POSTS), default=10)
    parser.add_argument("--select", dest="select_limit", type=bounded_int(MAX_SELECTED_POSTS), default=5)
    parser.add_argument(
        "--comments", dest="comments_limit",
        type=bounded_int(MAX_COMMENTS_PER_POST), default=30,
    )
    parser.add_argument(
        "--max-age-days", type=bounded_int(MAX_AGE_DAYS), default=7,
    )
    parser.add_argument(
        "--comment-sort",
        choices=("top", "new", "controversial", "confidence"),
        default="top",
    )
    parser.add_argument("--timeout", type=bounded_int(60), default=30)
    parser.add_argument("--pause", type=float, default=0.5)
    args = parser.parse_args(argv)
    if args.pause < 0.25:
        parser.error("--pause must be at least 0.25 seconds")
    return Config(
        hot_limit=args.hot_limit,
        new_limit=args.new_limit,
        select_limit=args.select_limit,
        comments_limit=args.comments_limit,
        max_age_days=args.max_age_days,
        comment_sort=args.comment_sort,
        output_path=DEFAULT_OUTPUT,
        request_timeout=args.timeout,
        pause_seconds=args.pause,
    )


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    config = parse_args(argv)
    try:
        config.output_path.parent.mkdir(parents=True, exist_ok=True)
        purged = purge_stale_outputs(config.output_path.parent)
        result = collect(config)
        config.output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except (CollectorError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Purged {purged} stale JSON output(s).")
    print(f"Saved {len(result['posts'])} selected posts to {config.output_path.resolve()}")
    print(f"Delete or re-run within {RETENTION_HOURS} hours; stale outputs auto-purge on next run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
