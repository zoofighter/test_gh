import logging
from datetime import datetime

import feedparser

from src.collectors.base import BaseCollector, NewsItem

logger = logging.getLogger(__name__)

DEFAULT_FEEDS = [
    {"name": "한국경제", "url": "https://www.hankyung.com/feed/stock"},
    {"name": "매일경제", "url": "https://www.mk.co.kr/rss/30100041/"},
]


class RssCollector(BaseCollector):
    source_name = "rss"

    def collect(self) -> list[NewsItem]:
        rss_cfg = self.config.get("collectors", {}).get("rss", {})
        if not rss_cfg.get("enabled", True):
            return []

        feeds = rss_cfg.get("feeds", DEFAULT_FEEDS)
        items = []

        for feed_info in feeds:
            name = feed_info.get("name", "unknown")
            url = feed_info.get("url", "")
            if not url:
                continue
            items.extend(self._parse_feed(name, url))

        logger.info(f"[RSS] 수집 완료: {len(items)}건")
        return items

    def _parse_feed(self, feed_name: str, feed_url: str) -> list[NewsItem]:
        items = []
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")
                published = entry.get("published", "")

                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6]).isoformat()
                    except Exception:
                        pub_date = published
                else:
                    pub_date = published

                if title:
                    items.append(NewsItem(
                        source="rss",
                        title=title,
                        url=link,
                        content=summary,
                        published_at=pub_date,
                        extra={"feed_name": feed_name},
                    ))
        except Exception as e:
            logger.warning(f"[RSS] {feed_name} 피드 수집 실패: {e}")
        return items
