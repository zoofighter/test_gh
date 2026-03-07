import logging
from datetime import datetime, timedelta

import yfinance as yf

from src.database.repository import Repository

logger = logging.getLogger(__name__)


def fetch_us_stock_prices(tickers: list[str], repo: Repository, days: int = 5):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days + 10)

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date.strftime("%Y-%m-%d"),
                              end=end_date.strftime("%Y-%m-%d"))
            if df.empty:
                continue

            df = df.tail(days)
            prev_close = None
            for date_idx, row in df.iterrows():
                date_str = date_idx.strftime("%Y-%m-%d")
                close = float(row["Close"])
                volume = int(row["Volume"])

                if prev_close and prev_close > 0:
                    change_pct = ((close - prev_close) / prev_close) * 100
                else:
                    change_pct = 0.0

                repo.upsert_price(ticker, date_str, close, volume, round(change_pct, 2))
                prev_close = close

            logger.debug(f"[US] {ticker} 주가 {len(df)}일치 저장")
        except Exception as e:
            logger.warning(f"[US] {ticker} 주가 조회 실패: {e}")
