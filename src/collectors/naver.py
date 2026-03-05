import logging
import time

import requests
from bs4 import BeautifulSoup

from src.collectors.base import BaseCollector, NewsItem

logger = logging.getLogger(__name__)

NAVER_FINANCE_NEWS_URL = "https://finance.naver.com/news/mainnews.naver"
NAVER_STOCK_NEWS_URL = "https://finance.naver.com/item/news.naver"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


class NaverCollector(BaseCollector):
    source_name = "naver"

    def collect(self) -> list[NewsItem]:
        naver_cfg = self.config.get("collectors", {}).get("naver", {})
        if not naver_cfg.get("enabled", True):
            return []

        max_pages = naver_cfg.get("max_pages", 3)
        items = []

        # 메인 금융뉴스 수집
        items.extend(self._collect_main_news(max_pages))

        # 관심 종목 뉴스 수집
        watchlist = self.config.get("watchlist", {}).get("kr", [])
        for code in watchlist:
            items.extend(self._collect_stock_news(code))
            time.sleep(0.5)

        logger.info(f"[Naver] 수집 완료: {len(items)}건")
        return items

    def _collect_main_news(self, max_pages: int) -> list[NewsItem]:
        items = []
        for page in range(1, max_pages + 1):
            try:
                resp = requests.get(
                    NAVER_FINANCE_NEWS_URL,
                    params={"page": page},
                    headers=HEADERS,
                    timeout=10,
                )
                resp.raise_for_status()
                resp.encoding = "euc-kr"
                soup = BeautifulSoup(resp.text, "html.parser")

                articles = soup.select("li.block1")
                for article in articles:
                    a_tag = article.select_one("dd.articleSubject a")
                    if not a_tag:
                        a_tag = article.select_one("a")
                    if not a_tag:
                        continue

                    title = a_tag.get_text(strip=True)
                    href = a_tag.get("href", "")
                    if href and not href.startswith("http"):
                        href = "https://finance.naver.com" + href

                    summary_tag = article.select_one("dd.articleSummary")
                    summary = summary_tag.get_text(strip=True) if summary_tag else ""

                    date_tag = article.select_one("span.wdate")
                    pub_date = date_tag.get_text(strip=True) if date_tag else ""

                    if title:
                        items.append(NewsItem(
                            source="naver",
                            title=title,
                            url=href,
                            content=summary,
                            published_at=pub_date,
                        ))
                time.sleep(0.3)
            except Exception as e:
                logger.warning(f"[Naver] 메인뉴스 {page}페이지 수집 실패: {e}")
        return items

    def _collect_stock_news(self, stock_code: str) -> list[NewsItem]:
        items = []
        try:
            resp = requests.get(
                NAVER_STOCK_NEWS_URL,
                params={"code": stock_code, "page": 1},
                headers=HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            rows = soup.select("table.type5 tbody tr")
            for row in rows:
                a_tag = row.select_one("td.title a")
                if not a_tag:
                    continue
                title = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")
                if href and not href.startswith("http"):
                    href = "https://finance.naver.com" + href

                date_tag = row.select_one("td.date")
                pub_date = date_tag.get_text(strip=True) if date_tag else ""

                items.append(NewsItem(
                    source="naver",
                    title=title,
                    url=href,
                    content="",
                    published_at=pub_date,
                    stock_code=stock_code,
                ))
        except Exception as e:
            logger.warning(f"[Naver] 종목뉴스 {stock_code} 수집 실패: {e}")
        return items
