import logging
import time

import requests
from bs4 import BeautifulSoup

from src.collectors.base import BaseCollector, NewsItem

logger = logging.getLogger(__name__)

NAVER_DISCUSSION_URL = "https://finance.naver.com/item/board.naver"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


class NaverDiscussionCollector(BaseCollector):
    source_name = "naver_discussion"

    def collect(self) -> list[NewsItem]:
        disc_cfg = self.config.get("collectors", {}).get("naver_discussion", {})
        if not disc_cfg.get("enabled", False):
            return []

        watchlist = self.config.get("watchlist", {}).get("kr", [])
        if not watchlist:
            logger.info("[NaverDiscussion] 관심 종목이 설정되지 않아 건너뜁니다.")
            return []

        max_pages = disc_cfg.get("max_pages", 2)
        min_views = disc_cfg.get("min_views", 500)
        items = []

        for code in watchlist:
            items.extend(self._collect_discussions(code, max_pages, min_views))
            time.sleep(0.5)

        logger.info(f"[NaverDiscussion] 수집 완료: {len(items)}건")
        return items

    def _collect_discussions(self, stock_code: str, max_pages: int,
                             min_views: int) -> list[NewsItem]:
        items = []
        for page in range(1, max_pages + 1):
            try:
                resp = requests.get(
                    NAVER_DISCUSSION_URL,
                    params={"code": stock_code, "page": page},
                    headers=HEADERS,
                    timeout=10,
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                rows = soup.select("table.type2 tbody tr")
                for row in rows:
                    cells = row.select("td")
                    if len(cells) < 6:
                        continue

                    # 제목
                    title_tag = cells[1].select_one("a")
                    if not title_tag:
                        continue
                    title = title_tag.get("title", title_tag.get_text(strip=True))
                    href = title_tag.get("href", "")
                    if href and not href.startswith("http"):
                        href = "https://finance.naver.com" + href

                    # 조회수
                    views_text = cells[3].get_text(strip=True).replace(",", "")
                    try:
                        views = int(views_text)
                    except ValueError:
                        views = 0

                    # 조회수 필터
                    if views < min_views:
                        continue

                    # 날짜
                    date_text = cells[0].get_text(strip=True)

                    # 작성자
                    author_tag = cells[2].select_one("a")
                    author = author_tag.get_text(strip=True) if author_tag else ""

                    # 공감/비공감
                    agree = cells[4].get_text(strip=True) if len(cells) > 4 else "0"
                    disagree = cells[5].get_text(strip=True) if len(cells) > 5 else "0"

                    items.append(NewsItem(
                        source="naver_discussion",
                        title=title,
                        url=href,
                        content=f"조회 {views} | 공감 {agree} | 비공감 {disagree}",
                        published_at=date_text,
                        stock_code=stock_code,
                        extra={
                            "author": author,
                            "views": views,
                            "agree": agree,
                            "disagree": disagree,
                        },
                    ))

                time.sleep(0.3)
            except Exception as e:
                logger.warning(f"[NaverDiscussion] {stock_code} page {page} 수집 실패: {e}")

        return items
