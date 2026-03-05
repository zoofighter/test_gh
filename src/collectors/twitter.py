import logging
import time

import requests
from bs4 import BeautifulSoup

from src.collectors.base import BaseCollector, NewsItem

logger = logging.getLogger(__name__)

# Nitter 인스턴스를 통한 무료 수집 (X/Twitter API는 유료)
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
]

# 주식 관련 트위터 검색 키워드
DEFAULT_SEARCH_QUERIES_KR = ["코스피", "코스닥", "주식", "공시", "실적"]
DEFAULT_SEARCH_QUERIES_US = ["$AAPL", "$TSLA", "$NVDA", "stock market", "earnings"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


class TwitterCollector(BaseCollector):
    source_name = "twitter"

    def collect(self) -> list[NewsItem]:
        twitter_cfg = self.config.get("collectors", {}).get("twitter", {})
        if not twitter_cfg.get("enabled", False):
            return []

        items = []
        queries = twitter_cfg.get("search_queries", DEFAULT_SEARCH_QUERIES_KR + DEFAULT_SEARCH_QUERIES_US)
        max_per_query = twitter_cfg.get("max_per_query", 10)

        for query in queries:
            items.extend(self._search_nitter(query, max_per_query))
            time.sleep(1)

        logger.info(f"[Twitter] 수집 완료: {len(items)}건")
        return items

    def _search_nitter(self, query: str, max_items: int) -> list[NewsItem]:
        items = []
        for instance in NITTER_INSTANCES:
            try:
                resp = requests.get(
                    f"{instance}/search",
                    params={"f": "tweets", "q": query},
                    headers=HEADERS,
                    timeout=10,
                )
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                tweets = soup.select(".timeline-item")

                for tweet in tweets[:max_items]:
                    content_el = tweet.select_one(".tweet-content")
                    if not content_el:
                        continue
                    content = content_el.get_text(strip=True)

                    user_el = tweet.select_one(".username")
                    username = user_el.get_text(strip=True) if user_el else ""

                    date_el = tweet.select_one(".tweet-date a")
                    pub_date = ""
                    tweet_url = ""
                    if date_el:
                        pub_date = date_el.get("title", "")
                        href = date_el.get("href", "")
                        tweet_url = f"https://x.com{href}" if href else ""

                    title = content[:100] + ("..." if len(content) > 100 else "")

                    items.append(NewsItem(
                        source="twitter",
                        title=f"[@{username}] {title}",
                        url=tweet_url,
                        content=content,
                        published_at=pub_date,
                        extra={"username": username, "query": query},
                    ))

                if items:
                    break  # 성공한 인스턴스에서 중단
            except Exception as e:
                logger.debug(f"[Twitter] Nitter {instance} 실패: {e}")
                continue

        return items
