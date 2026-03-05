"""한국 종목 사전 로더 - pykrx 기반 종목명↔코드 매핑"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 모듈 레벨 캐시
_kr_name_to_code: dict[str, str] | None = None
_kr_code_to_name: dict[str, str] | None = None


def _load_kr_stocks() -> tuple[dict[str, str], dict[str, str]]:
    """pykrx에서 KOSPI + KOSDAQ 전체 종목 로드"""
    from pykrx import stock as pykrx_stock

    name_to_code = {}
    code_to_name = {}
    date = datetime.now().strftime("%Y%m%d")

    for market in ("KOSPI", "KOSDAQ"):
        try:
            tickers = pykrx_stock.get_market_ticker_list(date, market=market)
            for code in tickers:
                try:
                    name = pykrx_stock.get_market_ticker_name(code)
                    if name and len(name) >= 2:
                        name_to_code[name] = code
                        code_to_name[code] = name
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"[KrStockDict] {market} 종목 목록 조회 실패: {e}")

    return name_to_code, code_to_name


def get_kr_name_to_code() -> dict[str, str]:
    """한국 종목명 → 종목코드 딕셔너리 반환 (캐시)"""
    global _kr_name_to_code, _kr_code_to_name
    if _kr_name_to_code is None:
        try:
            _kr_name_to_code, _kr_code_to_name = _load_kr_stocks()
            logger.info(f"[KrStockDict] {len(_kr_name_to_code)}개 한국 종목 로드 완료")
        except Exception as e:
            logger.warning(f"[KrStockDict] 종목 사전 로드 실패: {e}")
            _kr_name_to_code = {}
            _kr_code_to_name = {}
    return _kr_name_to_code


def get_kr_code_to_name() -> dict[str, str]:
    """한국 종목코드 → 종목명 딕셔너리 반환 (캐시)"""
    global _kr_code_to_name
    if _kr_code_to_name is None:
        get_kr_name_to_code()  # 함께 로드
    return _kr_code_to_name
