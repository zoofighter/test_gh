#!/usr/bin/env python3
"""주식 랭킹 뉴스 시스템 - 뉴스 수집"""

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


def main():
    parser = argparse.ArgumentParser(description="주식 랭킹 뉴스 시스템 - 뉴스 수집")
    parser.add_argument("-c", "--config", default="config.yaml", help="설정 파일 경로")
    parser.add_argument("-v", "--verbose", action="store_true", help="상세 로그 출력")
    parser.add_argument("--no-collect", action="store_true", help="뉴스 수집 건너뛰기")
    args = parser.parse_args()

    setup_logging(args.verbose)
    logging.info("=== 주식 랭킹 뉴스 수집 시작 ===")

    config = load_config(args.config)

    if not args.no_collect:
        news_items = collect_news(config)
        print_results(news_items)
    else:
        logging.info("뉴스 수집 건너뛰기")

    logging.info("=== 완료 ===")


if __name__ == "__main__":
    main()
