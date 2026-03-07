RANKING_SYSTEM_PROMPT = """당신은 주식 시장 뉴스 분석 전문가입니다.
주어진 뉴스와 주가 데이터를 분석하여 각 종목의 주가 영향력 점수를 산출합니다.

평가 기준 (가중치 설정에 따라 배점이 달라질 수 있음):
1. 뉴스 중복 보도량 (동일 이슈가 여러 매체에 보도된 정도)
   - 1개 매체: 낮음 / 3개 이상: 중간 / 5개 이상: 높음
2. 키워드 가중치 (핵심 키워드 포함 여부)
   - 최고: M&A, 인수합병, 상장폐지, 거래정지
   - 높음: 실적발표, 대규모 계약, 신약승인, 정부규제
   - 중간: 공시, 유상증자, 무상증자, 자사주
   - 낮음: 일반 뉴스, 시황 요약
3. 주가/거래량 변동 (최근 거래일 대비 변화)
   - 주가 ±5% 이상: 높음 / ±3% 이상: 중간 / ±1% 이상: 낮음
   - 거래량 3배 이상: 높음 / 2배 이상: 중간
4. 뉴스 소스 신뢰도
   - 최고: DART 공시, 금융감독원
   - 높음: 주요 경제지(한경, 매경), Reuters, Bloomberg
   - 중간: 네이버 뉴스, Yahoo Finance
   - 낮음: SNS, 커뮤니티

반드시 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요."""

RANKING_USER_PROMPT = """다음 종목들의 뉴스를 분석하여 주가 영향력 점수를 산출하세요.

[가중치 설정]
- 뉴스 중복 보도량: {weight_coverage}%
- 키워드 가중치: {weight_keyword}%
- 주가/거래량 변동: {weight_volume}%
- 뉴스 소스 신뢰도: {weight_source}%

{stock_news_data}

각 종목에 대해 아래 JSON 배열 형식으로 응답하세요:
[
  {{
    "stock_code": "종목코드",
    "stock_name": "종목명",
    "score": 총점(0~100),
    "news_count": 관련뉴스수,
    "keyword_score": 키워드점수(0~{max_keyword}),
    "volume_score": 거래량변동점수(0~{max_volume}),
    "price_score": 주가변동점수(0~{max_price}),
    "source_score": 소스신뢰도점수(0~{max_source}),
    "category": "주요카테고리(실적|공시|M&A|신사업|거시경제|섹터이슈|수급|정책·규제)",
    "summary": "핵심 뉴스 한줄 요약 (30자 이내)",
    "reason": "점수 산출 근거 한줄 설명 (50자 이내)"
  }}
]

점수가 높은 순서대로 정렬하세요."""

# 기본 가중치 (합계 100)
DEFAULT_WEIGHTS = {
    "coverage": 25,  # 뉴스 중복 보도량
    "keyword": 25,   # 키워드 가중치
    "volume": 25,    # 주가/거래량 변동
    "source": 25,    # 뉴스 소스 신뢰도
}


def get_weights(config: dict) -> dict:
    """config에서 가중치 설정을 가져오거나 기본값을 반환"""
    weights = config.get("ranking", {}).get("weights", DEFAULT_WEIGHTS)
    total = sum(weights.values())
    if total != 100:
        factor = 100 / total
        weights = {k: round(v * factor) for k, v in weights.items()}
    return weights


def build_ranking_prompt(stock_news_data: str, config: dict) -> str:
    """가중치 설정을 반영한 랭킹 프롬프트 생성"""
    weights = get_weights(config)
    return RANKING_USER_PROMPT.format(
        weight_coverage=weights["coverage"],
        weight_keyword=weights["keyword"],
        weight_volume=weights["volume"],
        weight_source=weights["source"],
        max_keyword=weights["keyword"],
        max_volume=weights["volume"],
        max_price=weights["volume"],
        max_source=weights["source"],
        stock_news_data=stock_news_data,
    )


# ============================================================
# 뉴스 개별 영향력 랭킹 프롬프트
# ============================================================

NEWS_RANKING_SYSTEM_PROMPT = """당신은 주식 시장 뉴스 분석 전문가입니다.
개별 뉴스 기사가 오늘 시장에 미치는 영향력 점수를 산출합니다.

평가 기준:
1. 보도 범위 (Coverage) - 동일 이슈가 여러 매체에 보도된 정도
   - 1개 매체: 낮음 / 3개 이상: 중간 / 5개 이상: 높음
2. 키워드 중요도 (Keyword) - 핵심 키워드 포함 여부
   - 최고: M&A, 인수합병, 상장폐지, 거래정지, merger, acquisition, delisting
   - 높음: 실적발표, 대규모 계약, 신약승인, FDA, earnings, contract
   - 중간: 공시, 유상증자, 무상증자, 자사주, 관세, regulation, tariff
   - 낮음: 일반 뉴스, 시황 요약
3. 소스 신뢰도 (Source Credibility) - 뉴스 출처의 공신력
   - 최고: DART 공시, 금융감독원, SEC
   - 높음: 주요 경제지(한경, 매경), Reuters, Bloomberg
   - 중간: 네이버 뉴스, Yahoo Finance, Google News
   - 낮음: SNS, Reddit, 커뮤니티
4. 시장 관련도 (Market Relevance) - 특정 종목 언급, 시장 전반 영향
   - 특정 종목의 실적/공시: 높음
   - 업종/섹터 전반 뉴스: 중간
   - 일반 경제 뉴스: 낮음

반드시 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요."""

NEWS_RANKING_USER_PROMPT = """다음 뉴스 기사들의 시장 영향력 점수를 개별적으로 산출하세요.

[가중치 설정]
- 보도 범위: {weight_coverage}점 만점
- 키워드 중요도: {weight_keyword}점 만점
- 소스 신뢰도: {weight_source}점 만점
- 시장 관련도: {weight_relevance}점 만점

{news_batch_data}

각 뉴스 기사에 대해 아래 JSON 배열 형식으로 응답하세요:
[
  {{
    "index": 기사번호(1부터),
    "score": 총점(0~100),
    "coverage_score": 보도범위점수(0~{weight_coverage}),
    "keyword_score": 키워드점수(0~{weight_keyword}),
    "source_credibility_score": 소스신뢰도점수(0~{weight_source}),
    "market_relevance_score": 시장관련도점수(0~{weight_relevance}),
    "impact_reason": "영향력 근거 한줄 설명 (50자 이내)"
  }}
]

점수가 높은 순서대로 정렬하세요."""


def format_news_batch_block(news_list: list[dict]) -> str:
    """뉴스 배치를 LLM 입력 텍스트 블록으로 포맷"""
    lines = []
    for i, news in enumerate(news_list, 1):
        source = news.get("source", "")
        title = news.get("title", "")
        category = news.get("category", "")
        stock_code = news.get("stock_code", "")
        stock_name = news.get("stock_name", "")
        coverage_count = news.get("coverage_count", 1)
        coverage_sources = news.get("coverage_sources", [])
        content_snippet = (news.get("content", "") or "")[:200]

        lines.append(f"--- 기사 #{i} ---")
        lines.append(f"출처: {source}")
        lines.append(f"제목: {title}")
        if category:
            lines.append(f"카테고리: {category}")
        if stock_code:
            lines.append(f"관련종목: {stock_name} ({stock_code})")
        sources_str = ", ".join(coverage_sources) if coverage_sources else source
        lines.append(f"보도 매체 수: {coverage_count}개 ({sources_str})")
        if content_snippet:
            lines.append(f"내용: {content_snippet}")
        lines.append("")

    return "\n".join(lines)


def build_news_ranking_prompt(news_batch_data: str, config: dict) -> str:
    """가중치 설정을 반영한 뉴스 랭킹 프롬프트 생성"""
    weights = get_weights(config)
    return NEWS_RANKING_USER_PROMPT.format(
        weight_coverage=weights["coverage"],
        weight_keyword=weights["keyword"],
        weight_source=weights["source"],
        weight_relevance=weights.get("volume", 25),
        news_batch_data=news_batch_data,
    )


def format_stock_news_block(stock_code: str, stock_name: str,
                            news_list: list[dict], price_data: list[dict]) -> str:
    lines = [f"=== {stock_name} ({stock_code}) ==="]

    if price_data:
        latest = price_data[0]
        lines.append(f"최근 종가: {latest.get('close', 'N/A')} | "
                     f"변동률: {latest.get('change_pct', 0):.2f}% | "
                     f"거래량: {latest.get('volume', 'N/A')}")
        if len(price_data) >= 2:
            prev = price_data[1]
            vol_change = ""
            if prev.get("volume") and prev["volume"] > 0:
                vol_ratio = latest.get("volume", 0) / prev["volume"]
                vol_change = f" (전일대비 {vol_ratio:.1f}배)"
            lines.append(f"전일 종가: {prev.get('close', 'N/A')} | "
                         f"거래량: {prev.get('volume', 'N/A')}{vol_change}")

        if len(price_data) >= 3:
            changes = [p.get("change_pct", 0) for p in price_data[:5]]
            avg_change = sum(changes) / len(changes)
            trend = "상승세" if avg_change > 0.5 else ("하락세" if avg_change < -0.5 else "보합")
            lines.append(f"최근 {len(changes)}일 추세: {trend} (평균 {avg_change:+.2f}%)")

    source_counts = {}
    for news in news_list:
        src = news.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1
    source_summary = ", ".join(f"{k}:{v}" for k, v in source_counts.items())
    lines.append(f"뉴스 소스 분포: {source_summary}")

    lines.append(f"관련 뉴스 ({len(news_list)}건):")
    for i, news in enumerate(news_list[:10], 1):
        source = news.get("source", "")
        title = news.get("title", "")
        category = news.get("category", "")
        cat_str = f" [{category}]" if category else ""
        lines.append(f"  {i}. [{source}]{cat_str} {title}")

    return "\n".join(lines)
