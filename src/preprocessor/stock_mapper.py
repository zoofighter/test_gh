import logging
import re

from src.collectors.base import NewsItem
from src.database.repository import Repository
from src.preprocessor.kr_stock_dict import get_kr_name_to_code

logger = logging.getLogger(__name__)


def map_stocks(news_items: list[NewsItem], repo: Repository) -> list[NewsItem]:
    # DB 등록 종목
    stocks = repo.get_all_stocks()
    name_to_code = {s["name"]: s["code"] for s in stocks}
    code_set = {s["code"] for s in stocks}

    # 한국 종목 사전 (pykrx) 병합 - DB에 없는 종목도 매핑 가능
    kr_dict = get_kr_name_to_code()
    all_name_to_code = {}
    all_name_to_code.update(kr_dict)
    all_name_to_code.update(name_to_code)  # DB 종목 우선

    # 긴 종목명 우선 매칭 (예: "SK하이닉스"를 "SK"보다 먼저)
    sorted_names = sorted(all_name_to_code.keys(), key=len, reverse=True)

    mapped = 0
    auto_registered = set()

    for item in news_items:
        if item.stock_code:
            continue

        text = f"{item.title} {item.content}"

        # 종목명 매핑 (긴 이름 우선)
        for name in sorted_names:
            if len(name) < 2:
                continue
            if name in text:
                code = all_name_to_code[name]
                item.stock_code = code
                item.stock_name = name
                mapped += 1

                # pykrx 사전에서 매칭된 종목을 DB에 자동 등록
                if code not in code_set and code not in auto_registered:
                    market = "KOSPI"  # pykrx 사전 종목은 한국 종목
                    repo.upsert_stock(code, name, market)
                    auto_registered.add(code)
                    code_set.add(code)

                break

        # 종목코드 패턴 매핑 (6자리 숫자 - 국내, 대문자 영문 - 미국)
        if not item.stock_code:
            kr_match = re.search(r'\b(\d{6})\b', text)
            if kr_match and kr_match.group(1) in code_set:
                item.stock_code = kr_match.group(1)
                matched_stock = next((s for s in stocks if s["code"] == item.stock_code), None)
                if matched_stock:
                    item.stock_name = matched_stock["name"]
                mapped += 1
                continue

            us_match = re.search(r'\b([A-Z]{1,5})\b', text)
            if us_match and us_match.group(1) in code_set:
                item.stock_code = us_match.group(1)
                item.stock_name = us_match.group(1)
                mapped += 1

    if auto_registered:
        logger.info(f"[StockMapper] {len(auto_registered)}개 한국 종목 자동 등록")
    logger.info(f"[StockMapper] {mapped}건 종목 매핑 완료")
    return news_items
