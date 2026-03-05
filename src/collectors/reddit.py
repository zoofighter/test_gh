import logging
from datetime import datetime

import requests

from src.collectors.base import BaseCollector, NewsItem

logger = logging.getLogger(__name__)

# Reddit JSON API (인증 불필요)
REDDIT_BASE = "https://www.reddit.com"

DEFAULT_SUBREDDITS = ["stocks", "wallstreetbets", "investing"]

HEADERS = {
    "User-Agent": "StockRankingNews/1.0 (stock news collector)"
}


class RedditCollector(BaseCollector):
    source_name = "reddit"

    def collect(self) -> list[NewsItem]:
        reddit_cfg = self.config.get("collectors", {}).get("reddit", {})
        if not reddit_cfg.get("enabled", False):
            return []

        subreddits = reddit_cfg.get("subreddits", DEFAULT_SUBREDDITS)
        min_score = reddit_cfg.get("min_score", 50)
        limit = reddit_cfg.get("limit", 25)
        items = []

        for sub in subreddits:
            items.extend(self._fetch_subreddit(sub, limit, min_score))

        logger.info(f"[Reddit] 수집 완료: {len(items)}건")
        return items

    def _fetch_subreddit(self, subreddit: str, limit: int,
                         min_score: int) -> list[NewsItem]:
        items = []
        try:
            url = f"{REDDIT_BASE}/r/{subreddit}/hot.json"
            resp = requests.get(
                url,
                params={"limit": limit},
                headers=HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            posts = data.get("data", {}).get("children", [])
            for post_wrap in posts:
                post = post_wrap.get("data", {})

                title = post.get("title", "")
                score = post.get("score", 0)
                num_comments = post.get("num_comments", 0)
                permalink = post.get("permalink", "")
                created_utc = post.get("created_utc", 0)
                selftext = post.get("selftext", "")
                link_flair = post.get("link_flair_text", "")
                author = post.get("author", "")
                is_stickied = post.get("stickied", False)

                # 고정 포스트 및 저품질 필터링
                if is_stickied or score < min_score:
                    continue

                if not title:
                    continue

                pub_date = ""
                if created_utc:
                    pub_date = datetime.utcfromtimestamp(created_utc).isoformat()

                post_url = f"https://www.reddit.com{permalink}" if permalink else ""
                flair_str = f" [{link_flair}]" if link_flair else ""

                # 본문은 300자까지만
                content_preview = selftext[:300] if selftext else ""

                items.append(NewsItem(
                    source="reddit",
                    title=f"[r/{subreddit}]{flair_str} {title}",
                    url=post_url,
                    content=content_preview,
                    published_at=pub_date,
                    extra={
                        "subreddit": subreddit,
                        "score": score,
                        "num_comments": num_comments,
                        "author": author,
                        "flair": link_flair,
                    },
                ))
        except Exception as e:
            logger.warning(f"[Reddit] r/{subreddit} 수집 실패: {e}")
        return items
