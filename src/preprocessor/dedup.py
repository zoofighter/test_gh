import logging
from difflib import SequenceMatcher

from src.collectors.base import NewsItem

logger = logging.getLogger(__name__)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def deduplicate(news_items: list[NewsItem], threshold: float = 0.8) -> list[NewsItem]:
    if not news_items:
        return []

    unique = []
    seen_titles = []  # list of (title, index_into_unique)

    for item in news_items:
        matched_idx = None
        for title, idx in seen_titles:
            if similarity(item.title, title) >= threshold:
                matched_idx = idx
                break

        if matched_idx is not None:
            # 중복 뉴스: 원본에 보도량 정보 추가
            canonical = unique[matched_idx]
            canonical.extra["coverage_count"] = canonical.extra.get("coverage_count", 1) + 1
            sources = canonical.extra.get("coverage_sources", [canonical.source])
            if item.source not in sources:
                sources.append(item.source)
            canonical.extra["coverage_sources"] = sources
        else:
            # 최초 등장: 보도량 초기화
            item.extra["coverage_count"] = item.extra.get("coverage_count", 1)
            item.extra["coverage_sources"] = item.extra.get("coverage_sources", [item.source])
            unique.append(item)
            seen_titles.append((item.title, len(unique) - 1))

    removed = len(news_items) - len(unique)
    if removed:
        logger.info(f"[Dedup] {removed}건 중복 제거 ({len(news_items)} → {len(unique)})")
    return unique
