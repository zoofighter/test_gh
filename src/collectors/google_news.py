import logging
from datetime import datetime

import feedparser

from src.collectors.base import BaseCollector, NewsItem

logger = logging.getLogger(__name__)

# Google News RSS - 금융/주식 관련 토픽
GOOGLE_NEWS_FEEDS = {
    "kr_business": "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNRGx6TVdZU0FtdHZLQUFQAQ?hl=ko&gl=KR&ceid=KR:ko",
    "us_business": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en&gl=US&ceid=US:en",
}

# 키워드 기반 검색 URL 템플릿
GOOGLE_NEWS_SEARCH = "https://news.google.com/rss/search?q={query}&hl={hl}&gl={gl}&ceid={ceid}"


class GoogleNewsCollector(BaseCollector):
    source_name = "google_news"

    def collect(self) -> list[NewsItem]:
        gn_cfg = self.config.get("collectors", {}).get("google_news", {})
        if not gn_cfg.get("enabled", False):
            return []

        items = []

        # 기본 금융 토픽 피드
        feeds = gn_cfg.get("feeds", ["kr_business", "us_business"])
        for feed_key in feeds:
            url = GOOGLE_NEWS_FEEDS.get(feed_key)
            if url:
                items.extend(self._parse_feed(feed_key, url))

        # 키워드 검색 피드
        search_queries = gn_cfg.get("search_queries", [])
        for q_cfg in search_queries:
            query = q_cfg.get("query", "")
            hl = q_cfg.get("hl", "ko")
            gl = q_cfg.get("gl", "KR")
            ceid = q_cfg.get("ceid", "KR:ko")
            if query:
                url = GOOGLE_NEWS_SEARCH.format(query=query, hl=hl, gl=gl, ceid=ceid)
                items.extend(self._parse_feed(f"search:{query}", url))

        logger.info(f"[GoogleNews] 수집 완료: {len(items)}건")
        return items

    def _parse_feed(self, feed_name: str, feed_url: str) -> list[NewsItem]:
        items = []
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                published = entry.get("published", "")
                source_tag = entry.get("source", {})
                source_name = source_tag.get("title", "") if isinstance(source_tag, dict) else ""

                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6]).isoformat()
                    except Exception:
                        pub_date = published
                else:
                    pub_date = published

                # Google News 제목에서 소스명 분리: "기사 제목 - 출처" 형태
                display_source = source_name
                if " - " in title and not source_name:
                    parts = title.rsplit(" - ", 1)
                    if len(parts) == 2:
                        title = parts[0].strip()
                        display_source = parts[1].strip()

                if title:
                    items.append(NewsItem(
                        source="google_news",
                        title=title,
                        url=link,
                        content=f"[{display_source}] {title}" if display_source else title,
                        published_at=pub_date,
                        extra={"feed": feed_name, "original_source": display_source},
                    ))
        except Exception as e:
            logger.warning(f"[GoogleNews] {feed_name} 수집 실패: {e}")
        return items
