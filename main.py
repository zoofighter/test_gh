#!/usr/bin/env python3
"""주식 랭킹 뉴스 시스템 - 뉴스 수집 + DB 저장"""

import argparse
import logging
import os
import sys

import yaml

from src.collectors.naver import NaverCollector
from src.collectors.dart import DartCollector
from src.collectors.yahoo import YahooCollector
from src.collectors.rss import RssCollector
from src.collectors.twitter import TwitterCollector
from src.collectors.naver_discussion import NaverDiscussionCollector
from src.collectors.google_news import GoogleNewsCollector
from src.collectors.reddit import RedditCollector
from src.database.models import get_db_path, init_db
from src.database.repository import Repository
from src.preprocessor.dedup import deduplicate
from src.preprocessor.stock_mapper import map_stocks
from src.preprocessor.categorizer import categorize


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def load_config(config_path: str = "config.yaml") -> dict:
    if not os.path.exists(config_path):
        logging.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
        logging.error("config.yaml을 생성한 후 설정을 입력하세요.")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect_news(config: dict) -> list:
    """모든 소스에서 뉴스 수집"""
    collectors = [
        NaverCollector(config),
        DartCollector(config),
        YahooCollector(config),
        RssCollector(config),
        TwitterCollector(config),
        NaverDiscussionCollector(config),
        GoogleNewsCollector(config),
        RedditCollector(config),
    ]

    all_news = []
    for collector in collectors:
        try:
            items = collector.collect()
            all_news.extend(items)
            logging.info(f"[{collector.source_name}] {len(items)}건 수집")
        except Exception as e:
            logging.error(f"[{collector.source_name}] 수집 실패: {e}")

    logging.info(f"총 {len(all_news)}건 뉴스 수집 완료")
    return all_news


def preprocess(news_items: list, repo: Repository) -> list:
    """전처리: 중복 제거 → 종목 매핑 → 카테고리 분류"""
    news_items = deduplicate(news_items)
    news_items = map_stocks(news_items, repo)
    news_items = categorize(news_items)
    return news_items


def register_stocks(repo: Repository, news_items: list):
    """뉴스에 포함된 종목코드를 stocks 테이블에 자동 등록"""
    registered = set()
    for item in news_items:
        if not item.stock_code or item.stock_code in registered:
            continue
        if repo.get_stock(item.stock_code):
            registered.add(item.stock_code)
            continue

        # 시장 자동 판별: 숫자 6자리 → KOSPI, 그 외 → NYSE
        code = item.stock_code
        if code.isdigit() and len(code) == 6:
            market = "KOSPI"
        else:
            market = "NYSE"

        name = item.stock_name if item.stock_name else code
        repo.upsert_stock(code=code, name=name, market=market)
        registered.add(code)
        logging.info(f"종목 등록: {code} ({name}, {market})")


def save_to_db(repo: Repository, news_items: list) -> int:
    """수집된 뉴스를 DB에 저장 (URL 중복 체크)"""
    # 종목 먼저 등록 (FK 제약 충족)
    register_stocks(repo, news_items)

    saved = 0
    skipped = 0

    for item in news_items:
        if item.url and repo.news_exists(item.url):
            skipped += 1
            continue

        repo.insert_news(
            source=item.source,
            title=item.title,
            url=item.url,
            content=item.content,
            published_at=item.published_at,
            category=item.category,
            stock_code=item.stock_code if item.stock_code else None,
        )
        saved += 1

    logging.info(f"DB 저장: {saved}건 신규, {skipped}건 중복 스킵")
    return saved


def print_results(news_items: list):
    """수집 결과를 터미널에 출력"""
    if not news_items:
        print("\n수집된 뉴스가 없습니다.")
        return

    print(f"\n{'='*80}")
    print(f" 수집된 뉴스: 총 {len(news_items)}건")
    print(f"{'='*80}")

    # 소스별 통계
    source_counts = {}
    for item in news_items:
        source_counts[item.source] = source_counts.get(item.source, 0) + 1

    print("\n[소스별 수집 현황]")
    for source, count in sorted(source_counts.items()):
        print(f"  {source:20s}: {count}건")

    print(f"\n[최근 수집 뉴스 (상위 30건)]")
    print(f"{'-'*80}")
    for i, item in enumerate(news_items[:30], 1):
        stock_info = f" [{item.stock_code}]" if item.stock_code else ""
        print(f"  {i:2d}. [{item.source}]{stock_info} {item.title}")
        if item.published_at:
            print(f"      발행: {item.published_at}")
        print()


def print_db_stats(repo: Repository):
    """DB 저장 현황 출력"""
    recent = repo.get_recent_news(days=1)
    source_counts = {}
    for row in recent:
        source_counts[row["source"]] = source_counts.get(row["source"], 0) + 1

    print(f"\n[DB 저장 현황 (최근 24시간)]")
    print(f"{'-'*40}")
    for source, count in sorted(source_counts.items()):
        print(f"  {source:20s}: {count}건")
    print(f"  {'합계':20s}: {len(recent)}건")


def main():
    parser = argparse.ArgumentParser(description="주식 랭킹 뉴스 시스템 - 뉴스 수집")
    parser.add_argument("-c", "--config", default="config.yaml", help="설정 파일 경로")
    parser.add_argument("-v", "--verbose", action="store_true", help="상세 로그 출력")
    parser.add_argument("--no-collect", action="store_true", help="뉴스 수집 건너뛰기")
    parser.add_argument("--no-save", action="store_true", help="DB 저장 건너뛰기")
    parser.add_argument("--stats", action="store_true", help="DB 저장 현황만 조회")
    args = parser.parse_args()

    setup_logging(args.verbose)
    logging.info("=== 주식 랭킹 뉴스 수집 시작 ===")

    config = load_config(args.config)

    # DB 초기화
    db_path = get_db_path(config)
    init_db(db_path)
    repo = Repository(db_path)
    logging.info(f"DB 경로: {db_path}")

    # DB 현황만 조회
    if args.stats:
        print_db_stats(repo)
        return

    # 뉴스 수집
    if not args.no_collect:
        news_items = collect_news(config)

        # 전처리
        logging.info("--- 전처리 시작 ---")
        news_items = preprocess(news_items, repo)

        print_results(news_items)

        # DB 저장
        if not args.no_save:
            save_to_db(repo, news_items)
            print_db_stats(repo)

        # 30일 지난 데이터 정리
        repo.cleanup_old_data(days=30)
    else:
        logging.info("뉴스 수집 건너뛰기")

    logging.info("=== 완료 ===")


if __name__ == "__main__":
    main()
