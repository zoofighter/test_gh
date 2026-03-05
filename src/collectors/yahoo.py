import logging
from datetime import datetime

import yfinance as yf

from src.collectors.base import BaseCollector, NewsItem

logger = logging.getLogger(__name__)

DEFAULT_US_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"]


class YahooCollector(BaseCollector):
    source_name = "yahoo"

    def collect(self) -> list[NewsItem]:
        yahoo_cfg = self.config.get("collectors", {}).get("yahoo", {})
        if not yahoo_cfg.get("enabled", True):
            return []

        watchlist = self.config.get("watchlist", {}).get("us", [])
        tickers = watchlist if watchlist else DEFAULT_US_TICKERS

        items = []
        for ticker in tickers:
            items.extend(self._collect_ticker_news(ticker))

        logger.info(f"[Yahoo] 수집 완료: {len(items)}건")
        return items

    def _collect_ticker_news(self, ticker: str) -> list[NewsItem]:
        items = []
        try:
            stock = yf.Ticker(ticker)
            news_list = stock.news or []

            for news in news_list:
                title, summary, pub_date, publisher, link = "", "", "", "", ""

                # 새 API: {"id": ..., "content": {"title": ..., "summary": ...}}
                content = news.get("content", {})
                if isinstance(content, dict) and content.get("title"):
                    title = content.get("title", "")
                    summary = content.get("summary", "")
                    pub_date = content.get("pubDate", "")
                    provider = content.get("provider", {})
                    publisher = provider.get("displayName", "") if isinstance(provider, dict) else ""
                    link = news.get("link", "")
                    if not link:
                        news_id = news.get("id", "")
                        if news_id:
                            link = f"https://finance.yahoo.com/news/{news_id}"
                else:
                    # 이전 API 호환
                    title = news.get("title", "")
                    publisher = news.get("publisher", "")
                    link = news.get("link", "")
                    pub_ts = news.get("providerPublishTime", 0)
                    if pub_ts:
                        pub_date = datetime.fromtimestamp(pub_ts).isoformat()

                if not title:
                    continue

                # ISO 날짜 정규화
                if pub_date and "T" in pub_date:
                    try:
                        pub_date = datetime.fromisoformat(
                            pub_date.replace("Z", "+00:00")
                        ).isoformat()
                    except Exception:
                        pass

                display = f"[{publisher}] {summary}" if summary else f"[{publisher}] {title}"

                items.append(NewsItem(
                    source="yahoo",
                    title=title,
                    url=link,
                    content=display,
                    published_at=pub_date,
                    stock_code=ticker,
                    stock_name=ticker,
                    extra={"publisher": publisher},
                ))
        except Exception as e:
            logger.warning(f"[Yahoo] {ticker} 뉴스 수집 실패: {e}")
        return items
