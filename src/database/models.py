import sqlite3
import os


def get_db_path(config: dict) -> str:
    return config.get("database", {}).get("path", "data/stock_ranking.db")


def get_connection(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS stocks (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            market TEXT NOT NULL,
            sector TEXT
        );

        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT,
            content TEXT,
            published_at DATETIME,
            collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            category TEXT,
            stock_code TEXT,
            FOREIGN KEY (stock_code) REFERENCES stocks(code)
        );

        CREATE INDEX IF NOT EXISTS idx_news_stock_code ON news(stock_code);
        CREATE INDEX IF NOT EXISTS idx_news_collected_at ON news(collected_at);
        CREATE INDEX IF NOT EXISTS idx_news_source ON news(source);

        CREATE TABLE IF NOT EXISTS stock_prices (
            stock_code TEXT,
            date DATE,
            close REAL,
            volume INTEGER,
            change_pct REAL,
            PRIMARY KEY (stock_code, date),
            FOREIGN KEY (stock_code) REFERENCES stocks(code)
        );

        CREATE TABLE IF NOT EXISTS rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date DATETIME,
            rank INTEGER,
            stock_code TEXT,
            stock_name TEXT,
            score REAL,
            news_count INTEGER,
            keyword_score REAL,
            volume_change_pct REAL,
            price_change_pct REAL,
            source_credibility REAL,
            top_news_title TEXT,
            top_news_url TEXT,
            summary TEXT,
            FOREIGN KEY (stock_code) REFERENCES stocks(code)
        );

        CREATE INDEX IF NOT EXISTS idx_rankings_run_date ON rankings(run_date);

        CREATE TABLE IF NOT EXISTS ranking_news (
            ranking_id INTEGER,
            news_id INTEGER,
            PRIMARY KEY (ranking_id, news_id),
            FOREIGN KEY (ranking_id) REFERENCES rankings(id),
            FOREIGN KEY (news_id) REFERENCES news(id)
        );

        CREATE TABLE IF NOT EXISTS news_rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date DATETIME,
            rank INTEGER,
            news_id INTEGER,
            title TEXT,
            source TEXT,
            url TEXT,
            score REAL,
            coverage_score REAL,
            keyword_score REAL,
            source_credibility_score REAL,
            market_relevance_score REAL,
            category TEXT,
            stock_code TEXT,
            stock_name TEXT,
            impact_reason TEXT,
            coverage_count INTEGER DEFAULT 1,
            coverage_sources TEXT,
            FOREIGN KEY (news_id) REFERENCES news(id)
        );

        CREATE INDEX IF NOT EXISTS idx_news_rankings_run_date ON news_rankings(run_date);
        CREATE INDEX IF NOT EXISTS idx_news_rankings_score ON news_rankings(score DESC);

        CREATE TABLE IF NOT EXISTS news_impact (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_ranking_id INTEGER,
            news_id INTEGER,
            stock_code TEXT NOT NULL,
            published_date TEXT NOT NULL,
            base_price REAL,
            price_1d REAL,
            price_1w REAL,
            price_1m REAL,
            change_pct_1d REAL,
            change_pct_1w REAL,
            change_pct_1m REAL,
            predicted_score REAL,
            calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (news_id) REFERENCES news(id),
            FOREIGN KEY (stock_code) REFERENCES stocks(code)
        );

        CREATE INDEX IF NOT EXISTS idx_news_impact_stock ON news_impact(stock_code);
        CREATE INDEX IF NOT EXISTS idx_news_impact_date ON news_impact(published_date);

        CREATE TABLE IF NOT EXISTS scheduler_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            schedule_name TEXT,
            started_at DATETIME NOT NULL,
            finished_at DATETIME,
            status TEXT NOT NULL DEFAULT 'running',
            attempt INTEGER DEFAULT 1,
            error_message TEXT,
            news_count INTEGER,
            ranking_count INTEGER,
            duration_sec REAL
        );

        CREATE INDEX IF NOT EXISTS idx_scheduler_log_started ON scheduler_log(started_at);
    """)

    conn.commit()
    conn.close()
