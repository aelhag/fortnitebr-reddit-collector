import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reddit_collector import (  # noqa: E402
    flatten_comments,
    merge_posts,
    parse_args,
    purge_stale_outputs,
    select_posts,
)


class CollectorLogicTests(unittest.TestCase):
    def test_merge_posts_deduplicates_and_combines_listings(self):
        hot = [{"post_id": "abc", "listings": ["hot"], "score": 10, "num_comments": 5}]
        new = [{"post_id": "abc", "listings": ["new"], "score": 12, "num_comments": 7}]
        merged = merge_posts(hot, new)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["listings"], ["hot", "new"])
        self.assertEqual(merged[0]["score"], 12)
        self.assertEqual(merged[0]["num_comments"], 7)

    def test_flatten_comments_omits_identity_and_deleted_content(self):
        tree = [
            {
                "kind": "t1",
                "data": {
                    "id": "c1",
                    "author": "should_not_be_exported",
                    "body": "Ranked matchmaking is broken for me.",
                    "score": 4,
                    "created_utc": 1_700_000_000,
                    "depth": 0,
                    "parent_id": "t3_p1",
                    "permalink": "/r/FortniteBR/comments/p1/x/c1/",
                    "replies": {
                        "data": {
                            "children": [
                                {
                                    "kind": "t1",
                                    "data": {
                                        "id": "c2",
                                        "author": "also_private",
                                        "body": "Same issue on console.",
                                        "score": 2,
                                        "created_utc": 1_700_000_100,
                                        "depth": 1,
                                        "parent_id": "t1_c1",
                                        "replies": "",
                                    },
                                }
                            ]
                        }
                    },
                },
            },
            {
                "kind": "t1",
                "data": {
                    "id": "c3", "author": "deleted_user", "body": "[deleted]",
                    "score": 0, "created_utc": 1_700_000_200, "replies": "",
                },
            },
            {"kind": "more", "data": {"children": ["x", "y"]}},
        ]
        comments, skipped = flatten_comments(tree, max_comments=10)
        self.assertEqual(len(comments), 2)
        self.assertEqual(skipped, 2)
        for comment in comments:
            self.assertNotIn("author", comment)
            self.assertNotIn("comment_id", comment)
            self.assertNotIn("parent_id", comment)
            self.assertNotIn("permalink", comment)
        self.assertEqual(comments[1]["depth"], 1)

    def test_select_posts_prefers_relevant_discussion(self):
        now = 1_800_000_000.0
        base = {
            "selftext": "", "permalink": "https://reddit.example/post",
            "upvote_ratio": 0.9, "flair": "Discussion", "over_18": False,
            "spoiler": False, "stickied": False, "locked": False,
            "listings": ["new"],
        }
        posts = [
            {
                **base, "post_id": "useful",
                "title": "New update broke voice chat and matchmaking",
                "created_utc": now - 3600, "score": 50, "num_comments": 60,
            },
            {
                **base, "post_id": "noise", "title": "Rate my locker",
                "created_utc": now - 1800, "score": 100, "num_comments": 3,
                "flair": "Humor",
            },
        ]
        selected = select_posts(posts, limit=1, max_age_days=7, now_epoch=now)
        self.assertEqual(selected[0]["post_id"], "useful")
        self.assertIn("technical_issue", selected[0]["matched_topics"])
        self.assertIn("safety_account_chat", selected[0]["matched_topics"])

    def test_cli_rejects_collection_above_hard_ceiling(self):
        with self.assertRaises(SystemExit):
            parse_args(["--comments", "31"])
        with self.assertRaises(SystemExit):
            parse_args(["--hot", "11"])

    def test_purge_stale_outputs_deletes_only_old_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old_file = root / "old.json"
            fresh_file = root / "fresh.json"
            keep_file = root / "notes.txt"
            for path in (old_file, fresh_file, keep_file):
                path.write_text("x", encoding="utf-8")
            old_time = time.time() - 25 * 3600
            os.utime(old_file, (old_time, old_time))
            deleted = purge_stale_outputs(root, retention_hours=24)
            self.assertEqual(deleted, 1)
            self.assertFalse(old_file.exists())
            self.assertTrue(fresh_file.exists())
            self.assertTrue(keep_file.exists())


if __name__ == "__main__":
    unittest.main()
