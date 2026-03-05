import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from src.database.models import get_connection


class Repository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    # --- stocks ---
    def upsert_stock(self, code: str, name: str, market: str, sector: str = None):
        conn = self._conn()
        conn.execute(
            "INSERT OR REPLACE INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
            (code, name, market, sector),
        )
        conn.commit()
        conn.close()

    def get_stock(self, code: str) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute("SELECT * FROM stocks WHERE code = ?", (code,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_stocks(self) -> list[dict]:
        conn = self._conn()
        rows = conn.execute("SELECT * FROM stocks").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # --- news ---
    def insert_news(self, source: str, title: str, url: str, content: str,
                    published_at: str, category: str = None, stock_code: str = None) -> int:
        conn = self._conn()
        cursor = conn.execute(
            """INSERT INTO news (source, title, url, content, published_at, category, stock_code)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (source, title, url, content, published_at, category, stock_code),
        )
        news_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return news_id

    def get_recent_news(self, days: int = 1, source: str = None) -> list[dict]:
        conn = self._conn()
        since = (datetime.now() - timedelta(days=days)).isoformat()
        if source:
            rows = conn.execute(
                "SELECT * FROM news WHERE collected_at >= ? AND source = ? ORDER BY published_at DESC",
                (since, source),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM news WHERE collected_at >= ? ORDER BY published_at DESC",
                (since,),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_news_by_stock(self, stock_code: str, days: int = 1) -> list[dict]:
        conn = self._conn()
        since = (datetime.now() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            "SELECT * FROM news WHERE stock_code = ? AND collected_at >= ? ORDER BY published_at DESC",
            (stock_code, since),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def news_exists(self, url: str) -> bool:
        conn = self._conn()
        row = conn.execute("SELECT 1 FROM news WHERE url = ?", (url,)).fetchone()
        conn.close()
        return row is not None

    # --- stock_prices ---
    def upsert_price(self, stock_code: str, date: str, close: float,
                     volume: int, change_pct: float):
        conn = self._conn()
        conn.execute(
            """INSERT OR REPLACE INTO stock_prices (stock_code, date, close, volume, change_pct)
               VALUES (?, ?, ?, ?, ?)""",
            (stock_code, date, close, volume, change_pct),
        )
        conn.commit()
        conn.close()

    def get_recent_prices(self, stock_code: str, days: int = 5) -> list[dict]:
        conn = self._conn()
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT * FROM stock_prices WHERE stock_code = ? AND date >= ? ORDER BY date DESC",
            (stock_code, since),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # --- rankings ---
    def insert_ranking(self, run_date: str, rank: int, stock_code: str,
                       stock_name: str, score: float, news_count: int,
                       keyword_score: float, volume_change_pct: float,
                       price_change_pct: float, source_credibility: float,
                       top_news_title: str, top_news_url: str,
                       summary: str, news_ids: list[int] = None) -> int:
        conn = self._conn()
        cursor = conn.execute(
            """INSERT INTO rankings
               (run_date, rank, stock_code, stock_name, score, news_count,
                keyword_score, volume_change_pct, price_change_pct, source_credibility,
                top_news_title, top_news_url, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_date, rank, stock_code, stock_name, score, news_count,
             keyword_score, volume_change_pct, price_change_pct, source_credibility,
             top_news_title, top_news_url, summary),
        )
        ranking_id = cursor.lastrowid
        if news_ids:
            for nid in news_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO ranking_news (ranking_id, news_id) VALUES (?, ?)",
                    (ranking_id, nid),
                )
        conn.commit()
        conn.close()
        return ranking_id

    def get_rankings_by_date(self, run_date: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM rankings WHERE date(run_date) = date(?) ORDER BY rank",
            (run_date,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_ranking_history(self, days: int = 30) -> list[dict]:
        conn = self._conn()
        since = (datetime.now() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            "SELECT DISTINCT date(run_date) as run_day, COUNT(*) as count FROM rankings WHERE run_date >= ? GROUP BY run_day ORDER BY run_day DESC",
            (since,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # --- news_rankings ---
    def insert_news_ranking(self, run_date: str, rank: int, news_id: int,
                            title: str, source: str, url: str, score: float,
                            coverage_score: float, keyword_score: float,
                            source_credibility_score: float,
                            market_relevance_score: float,
                            category: str, stock_code: str, stock_name: str,
                            impact_reason: str, coverage_count: int,
                            coverage_sources: str) -> int:
        conn = self._conn()
        cursor = conn.execute(
            """INSERT INTO news_rankings
               (run_date, rank, news_id, title, source, url, score,
                coverage_score, keyword_score, source_credibility_score,
                market_relevance_score, category, stock_code, stock_name,
                impact_reason, coverage_count, coverage_sources)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_date, rank, news_id, title, source, url, score,
             coverage_score, keyword_score, source_credibility_score,
             market_relevance_score, category, stock_code, stock_name,
             impact_reason, coverage_count, coverage_sources),
        )
        nrid = cursor.lastrowid
        conn.commit()
        conn.close()
        return nrid

    def get_news_rankings_by_date(self, run_date: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM news_rankings WHERE date(run_date) = date(?) ORDER BY rank",
            (run_date,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_latest_news_rankings(self) -> list[dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT run_date FROM news_rankings ORDER BY run_date DESC LIMIT 1"
        ).fetchone()
        if not row:
            conn.close()
            return []
        latest = row["run_date"]
        rows = conn.execute(
            "SELECT * FROM news_rankings WHERE run_date = ? ORDER BY rank",
            (latest,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_news_ranking_history(self, days: int = 30) -> list[dict]:
        conn = self._conn()
        since = (datetime.now() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            "SELECT DISTINCT date(run_date) as run_day, COUNT(*) as count "
            "FROM news_rankings WHERE run_date >= ? GROUP BY run_day ORDER BY run_day DESC",
            (since,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # --- news_impact ---
    def get_price_on_date(self, stock_code: str, target_date: str) -> Optional[float]:
        conn = self._conn()
        row = conn.execute(
            "SELECT close FROM stock_prices WHERE stock_code = ? AND date <= ? ORDER BY date DESC LIMIT 1",
            (stock_code, target_date),
        ).fetchone()
        conn.close()
        return row["close"] if row else None

    def get_price_after_date(self, stock_code: str, base_date: str, days_after: int) -> Optional[float]:
        conn = self._conn()
        target = (datetime.strptime(base_date, "%Y-%m-%d") + timedelta(days=days_after)).strftime("%Y-%m-%d")
        row = conn.execute(
            "SELECT close FROM stock_prices WHERE stock_code = ? AND date >= ? ORDER BY date ASC LIMIT 1",
            (stock_code, target),
        ).fetchone()
        conn.close()
        return row["close"] if row else None

    def insert_news_impact(self, news_ranking_id: int, news_id: int,
                           stock_code: str, published_date: str,
                           base_price: float, price_1d: float = None,
                           price_1w: float = None, price_1m: float = None,
                           change_pct_1d: float = None, change_pct_1w: float = None,
                           change_pct_1m: float = None, predicted_score: float = None) -> int:
        conn = self._conn()
        cursor = conn.execute(
            """INSERT INTO news_impact
               (news_ranking_id, news_id, stock_code, published_date,
                base_price, price_1d, price_1w, price_1m,
                change_pct_1d, change_pct_1w, change_pct_1m, predicted_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (news_ranking_id, news_id, stock_code, published_date,
             base_price, price_1d, price_1w, price_1m,
             change_pct_1d, change_pct_1w, change_pct_1m, predicted_score),
        )
        impact_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return impact_id

    def impact_exists(self, news_ranking_id: int) -> bool:
        conn = self._conn()
        row = conn.execute(
            "SELECT 1 FROM news_impact WHERE news_ranking_id = ?", (news_ranking_id,)
        ).fetchone()
        conn.close()
        return row is not None

    # --- cleanup ---
    def cleanup_old_data(self, days: int = 30):
        conn = self._conn()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn.execute("DELETE FROM news_impact WHERE published_date < ?", (cutoff[:10],))
        conn.execute("DELETE FROM news_rankings WHERE run_date < ?", (cutoff,))
        conn.execute("DELETE FROM ranking_news WHERE ranking_id IN (SELECT id FROM rankings WHERE run_date < ?)", (cutoff,))
        conn.execute("DELETE FROM rankings WHERE run_date < ?", (cutoff,))
        conn.execute("DELETE FROM news WHERE collected_at < ?", (cutoff,))
        conn.execute("DELETE FROM stock_prices WHERE date < ?", (cutoff[:10],))
        conn.commit()
        conn.close()
