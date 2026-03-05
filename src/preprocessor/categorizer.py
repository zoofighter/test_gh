import logging

from src.collectors.base import NewsItem

logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS = {
    "실적": ["실적", "영업이익", "매출", "순이익", "분기", "어닝", "earnings", "revenue", "profit", "EPS"],
    "공시": ["공시", "보고서", "신고", "disclosure", "filing", "report"],
    "M&A": ["인수", "합병", "M&A", "매각", "merger", "acquisition", "takeover"],
    "신사업": ["신사업", "진출", "사업 확장", "new business", "expansion", "launch"],
    "거시경제": ["금리", "환율", "GDP", "인플레이션", "기준금리", "interest rate", "inflation", "CPI", "Fed"],
    "섹터이슈": ["반도체", "2차전지", "배터리", "AI", "자율주행", "바이오", "semiconductor", "battery", "biotech"],
    "수급": ["외국인", "기관", "공매도", "수급", "매수", "매도", "foreign", "institutional", "short selling"],
    "정책·규제": ["정책", "규제", "법안", "제재", "관세", "regulation", "policy", "tariff", "sanction"],
}


def categorize(news_items: list[NewsItem]) -> list[NewsItem]:
    categorized = 0
    for item in news_items:
        if item.category:
            continue

        text = f"{item.title} {item.content}".lower()
        best_category = ""
        best_score = 0

        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > best_score:
                best_score = score
                best_category = category

        if best_category:
            item.category = best_category
            categorized += 1

    logger.info(f"[Categorizer] {categorized}건 카테고리 분류 완료")
    return news_items
