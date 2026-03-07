import logging
from datetime import datetime, timedelta

from pykrx import stock as pykrx_stock

from src.database.repository import Repository

logger = logging.getLogger(__name__)


def fetch_kr_stock_prices(stock_codes: list[str], repo: Repository, days: int = 5):
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days + 10)).strftime("%Y%m%d")

    for code in stock_codes:
        try:
            df = pykrx_stock.get_market_ohlcv(start_date, end_date, code)
            if df.empty:
                continue

            df = df.tail(days)
            prev_close = None
            for date_idx, row in df.iterrows():
                date_str = date_idx.strftime("%Y-%m-%d")
                close = float(row["종가"])
                volume = int(row["거래량"])

                if prev_close and prev_close > 0:
                    change_pct = ((close - prev_close) / prev_close) * 100
                else:
                    change_pct = 0.0

                repo.upsert_price(code, date_str, close, volume, round(change_pct, 2))
                prev_close = close

            logger.debug(f"[KR] {code} 주가 {len(df)}일치 저장")
        except Exception as e:
            logger.warning(f"[KR] {code} 주가 조회 실패: {e}")
