import json
import logging
from collections import defaultdict
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.ranking.prompts import (
    RANKING_SYSTEM_PROMPT,
    build_ranking_prompt,
    format_stock_news_block,
    NEWS_RANKING_SYSTEM_PROMPT,
    build_news_ranking_prompt,
    format_news_batch_block,
)
from src.database.repository import Repository

logger = logging.getLogger(__name__)

BATCH_SIZE = 10  # 한 번에 LLM에 보낼 종목 수
NEWS_BATCH_SIZE = 20  # 한 번에 LLM에 보낼 뉴스 수


def _create_online_llm(config: dict):
    """config의 online_llm 설정에서 온라인 LLM 클라이언트 생성"""
    ol_cfg = config.get("online_llm", {})
    if not ol_cfg.get("enabled", False):
        return None

    provider = ol_cfg.get("provider", "openai")
    api_key = ol_cfg.get("api_key", "")
    model = ol_cfg.get("model", "gpt-4o-mini")
    temperature = ol_cfg.get("temperature", 0.1)
    max_tokens = ol_cfg.get("max_tokens", 4096)

    if not api_key or api_key == "YOUR_API_KEY":
        logger.warning("[OnlineLLM] API 키가 설정되지 않았습니다.")
        return None

    try:
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(
                model=model,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            llm = ChatOpenAI(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        logger.info(f"[OnlineLLM] {provider}/{model} 초기화 완료")
        return llm
    except Exception as e:
        logger.warning(f"[OnlineLLM] 초기화 실패: {e}")
        return None

# 소스별 신뢰도 점수 (0~25)
SOURCE_CREDIBILITY = {
    "dart": 25,
    "yahoo": 18,
    "rss": 18,
    "naver": 15,
    "google_news": 14,
    "reddit": 8,
    "twitter": 8,
    "naver_discussion": 6,
}

# 키워드 등급별 점수 (높은 등급 우선 매칭)
HIGH_IMPACT_KEYWORDS = [
    (25, ["M&A", "인수합병", "상장폐지", "거래정지", "merger", "acquisition", "delisting",
          "bankruptcy", "파산"]),
    (20, ["실적발표", "대규모 계약", "신약승인", "FDA", "earnings", "contract", "revenue",
          "영업이익", "매출", "순이익"]),
    (15, ["공시", "유상증자", "무상증자", "자사주", "regulation", "tariff", "관세",
          "disclosure", "제재", "sanctions"]),
    (10, ["금리", "환율", "인플레이션", "Fed", "interest rate", "CPI", "GDP",
          "기준금리", "연준"]),
    (5, ["반도체", "2차전지", "AI", "배터리", "바이오", "semiconductor", "EV",
         "artificial intelligence"]),
]


class RankingEngine:
    def __init__(self, config: dict, repo: Repository):
        self.config = config
        self.repo = repo
        lm_cfg = config.get("lm_studio", {})
        self.llm = ChatOpenAI(
            base_url=lm_cfg.get("base_url", "http://localhost:1234/v1"),
            api_key=lm_cfg.get("api_key", "lm-studio"),
            model=lm_cfg.get("model", "local-model"),
            temperature=lm_cfg.get("temperature", 0.1),
        )
        self.online_llm = _create_online_llm(config)
        self._llm_available = True
        self._online_llm_available = True
        self.top_n = config.get("ranking", {}).get("top_n", 20)
        self.max_news_per_stock = config.get("ranking", {}).get("max_news_per_stock", 10)

    def run(self, news_items: list[dict]) -> list[dict]:
        # 종목별 뉴스 그룹핑
        stock_news = defaultdict(list)
        for item in news_items:
            code = item.get("stock_code")
            if code:
                stock_news[code].append(item)

        if not stock_news:
            logger.warning("[Ranking] 종목 매핑된 뉴스가 없습니다.")
            return []

        logger.info(f"[Ranking] {len(stock_news)}개 종목에 대해 랭킹 분석 시작")

        # 배치 처리
        all_results = []
        stock_codes = list(stock_news.keys())

        for i in range(0, len(stock_codes), BATCH_SIZE):
            batch_codes = stock_codes[i:i + BATCH_SIZE]
            batch_results = self._rank_batch(batch_codes, stock_news)
            all_results.extend(batch_results)

        # 점수순 정렬 후 상위 N개
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        ranked = all_results[:self.top_n]

        # 순위 부여
        for idx, item in enumerate(ranked, 1):
            item["rank"] = idx

        # DB 저장
        run_date = datetime.now().isoformat()
        self._save_rankings(run_date, ranked)

        logger.info(f"[Ranking] 랭킹 완료: Top {len(ranked)}개 종목")
        return ranked

    def _rank_batch(self, stock_codes: list[str],
                    stock_news: dict[str, list]) -> list[dict]:
        # 종목별 데이터 블록 생성
        blocks = []
        for code in stock_codes:
            news = stock_news[code][:self.max_news_per_stock]
            prices = self.repo.get_recent_prices(code, days=5)

            stock = self.repo.get_stock(code)
            name = stock["name"] if stock else code

            block = format_stock_news_block(code, name, news, prices)
            blocks.append(block)

        stock_news_data = "\n\n".join(blocks)
        prompt = build_ranking_prompt(stock_news_data, self.config)
        messages = [
            SystemMessage(content=RANKING_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        # 1차: 로컬 LLM
        if self._llm_available:
            try:
                response = self.llm.invoke(messages)
                return self._parse_response(response.content, stock_codes, stock_news)
            except Exception as e:
                logger.error(f"[Ranking] 로컬 LLM 호출 실패: {e}")
                self._llm_available = False

        # 2차: 온라인 LLM
        if self._online_llm_available and self.online_llm:
            try:
                response = self.online_llm.invoke(messages)
                return self._parse_response(response.content, stock_codes, stock_news)
            except Exception as e:
                logger.error(f"[Ranking] 온라인 LLM 호출 실패: {e}")
                self._online_llm_available = False

        # 3차: 규칙 기반
        return self._fallback_ranking(stock_codes, stock_news)

    def _parse_response(self, response_text: str, stock_codes: list[str],
                        stock_news: dict) -> list[dict]:
        try:
            text = response_text.strip()
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                text = text[start:end]
            results = json.loads(text)
            if isinstance(results, list):
                for r in results:
                    code = r.get("stock_code", "")
                    news = stock_news.get(code, [])
                    if news:
                        r["top_news_title"] = news[0].get("title", "")
                        r["top_news_url"] = news[0].get("url", "")
                    r["news_count"] = len(stock_news.get(code, []))
                return results
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[Ranking] LLM 응답 파싱 실패: {e}")

        return self._fallback_ranking(stock_codes, stock_news)

    def _fallback_ranking(self, stock_codes: list[str],
                          stock_news: dict) -> list[dict]:
        """LLM 실패 시 뉴스 수 기반 간단 랭킹"""
        logger.info("[Ranking] 폴백 랭킹 사용 (뉴스 수 기반)")
        results = []
        for code in stock_codes:
            news = stock_news.get(code, [])
            stock = self.repo.get_stock(code)
            name = stock["name"] if stock else code
            prices = self.repo.get_recent_prices(code, days=2)

            price_change = prices[0]["change_pct"] if prices else 0
            volume_change = 0
            if len(prices) >= 2 and prices[1]["volume"] > 0:
                volume_change = (prices[0]["volume"] / prices[1]["volume"] - 1) * 100

            score = min(100, len(news) * 15 + abs(price_change) * 2 + abs(volume_change) * 0.5)

            results.append({
                "stock_code": code,
                "stock_name": name,
                "score": round(score, 1),
                "news_count": len(news),
                "keyword_score": 0,
                "volume_score": round(abs(volume_change) * 0.5, 1),
                "price_score": round(abs(price_change) * 2, 1),
                "source_score": 0,
                "category": news[0].get("category", "") if news else "",
                "summary": news[0].get("title", "") if news else "",
                "reason": "폴백 랭킹 (뉴스 수 + 주가변동 기반)",
                "top_news_title": news[0].get("title", "") if news else "",
                "top_news_url": news[0].get("url", "") if news else "",
            })
        return results

    def _save_rankings(self, run_date: str, rankings: list[dict]):
        for r in rankings:
            news_in_db = self.repo.get_news_by_stock(r["stock_code"], days=1)
            news_ids = [n["id"] for n in news_in_db]

            self.repo.insert_ranking(
                run_date=run_date,
                rank=r.get("rank", 0),
                stock_code=r.get("stock_code", ""),
                stock_name=r.get("stock_name", ""),
                score=r.get("score", 0),
                news_count=r.get("news_count", 0),
                keyword_score=r.get("keyword_score", 0),
                volume_change_pct=r.get("volume_score", 0),
                price_change_pct=r.get("price_score", 0),
                source_credibility=r.get("source_score", 0),
                top_news_title=r.get("top_news_title", ""),
                top_news_url=r.get("top_news_url", ""),
                summary=r.get("summary", ""),
                news_ids=news_ids,
            )


class NewsRankingEngine:
    """개별 뉴스 영향력 랭킹 엔진"""

    def __init__(self, config: dict, repo: Repository):
        self.config = config
        self.repo = repo
        lm_cfg = config.get("lm_studio", {})
        self.llm = ChatOpenAI(
            base_url=lm_cfg.get("base_url", "http://localhost:1234/v1"),
            api_key=lm_cfg.get("api_key", "lm-studio"),
            model=lm_cfg.get("model", "local-model"),
            temperature=lm_cfg.get("temperature", 0.1),
        )
        self.online_llm = _create_online_llm(config)
        self.top_n = config.get("ranking", {}).get("top_n", 30)
        self.batch_size = config.get("ranking", {}).get("news_batch_size", NEWS_BATCH_SIZE)
        self._llm_available = True
        self._online_llm_available = True

    def run(self, news_items: list[dict]) -> list[dict]:
        if not news_items:
            return []

        logger.info(f"[NewsRanking] {len(news_items)}건 뉴스에 대해 개별 영향력 점수 산출 시작")

        all_scored = []
        for i in range(0, len(news_items), self.batch_size):
            batch = news_items[i:i + self.batch_size]
            scored = self._score_batch(batch)
            all_scored.extend(scored)

        all_scored.sort(key=lambda x: x.get("score", 0), reverse=True)
        ranked = all_scored[:self.top_n]

        for idx, item in enumerate(ranked, 1):
            item["rank"] = idx

        run_date = datetime.now().isoformat()
        self._save_news_rankings(run_date, ranked)

        logger.info(f"[NewsRanking] 완료: Top {len(ranked)}건")
        return ranked

    def _score_batch(self, batch: list[dict]) -> list[dict]:
        prompt_data = format_news_batch_block(batch)
        prompt = build_news_ranking_prompt(prompt_data, self.config)
        messages = [
            SystemMessage(content=NEWS_RANKING_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        # 1차: 로컬 LLM
        if self._llm_available:
            try:
                response = self.llm.invoke(messages)
                return self._parse_news_response(response.content, batch)
            except Exception as e:
                logger.error(f"[NewsRanking] 로컬 LLM 호출 실패: {e}")
                self._llm_available = False

        # 2차: 온라인 LLM
        if self._online_llm_available and self.online_llm:
            try:
                response = self.online_llm.invoke(messages)
                return self._parse_news_response(response.content, batch)
            except Exception as e:
                logger.error(f"[NewsRanking] 온라인 LLM 호출 실패: {e}")
                self._online_llm_available = False

        # 3차: 규칙 기반
        return self._fallback_news_ranking(batch)

    def _parse_news_response(self, response_text: str, batch: list[dict]) -> list[dict]:
        try:
            text = response_text.strip()
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                text = text[start:end]
            results = json.loads(text)
            if isinstance(results, list):
                scored = []
                for r in results:
                    idx = r.get("index", 0) - 1  # 1-based → 0-based
                    if 0 <= idx < len(batch):
                        item = batch[idx]
                        scored.append({
                            "title": item.get("title", ""),
                            "source": item.get("source", ""),
                            "url": item.get("url", ""),
                            "score": r.get("score", 0),
                            "coverage_score": r.get("coverage_score", 0),
                            "keyword_score": r.get("keyword_score", 0),
                            "source_credibility_score": r.get("source_credibility_score", 0),
                            "market_relevance_score": r.get("market_relevance_score", 0),
                            "category": item.get("category", ""),
                            "stock_code": item.get("stock_code", ""),
                            "stock_name": item.get("stock_name", ""),
                            "impact_reason": r.get("impact_reason", ""),
                            "coverage_count": item.get("coverage_count", 1),
                            "coverage_sources": item.get("coverage_sources", []),
                            "news_id": item.get("id"),
                        })
                if scored:
                    return scored
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[NewsRanking] LLM 응답 파싱 실패: {e}")

        return self._fallback_news_ranking(batch)

    def _fallback_news_ranking(self, batch: list[dict]) -> list[dict]:
        """LLM 실패 시 규칙 기반 개별 뉴스 점수 산출"""
        logger.info(f"[NewsRanking] 폴백 랭킹 사용 ({len(batch)}건)")
        results = []
        for item in batch:
            coverage_count = item.get("coverage_count", 1)
            source = item.get("source", "")
            title = item.get("title", "")
            content = item.get("content", "")
            text = f"{title} {content}".lower()
            stock_code = item.get("stock_code", "")

            # 1. 보도 범위 (0~25)
            coverage_score = min(25, coverage_count * 8)

            # 2. 키워드 중요도 (0~25)
            keyword_score = self._compute_keyword_score(text)

            # 3. 소스 신뢰도 (0~25)
            source_score = SOURCE_CREDIBILITY.get(source, 10)

            # 4. 시장 관련도 (0~25)
            relevance_score = 0
            if stock_code:
                relevance_score += 12
                prices = self.repo.get_recent_prices(stock_code, days=2)
                if prices and abs(prices[0].get("change_pct", 0)) >= 3:
                    relevance_score += 8
                elif prices and abs(prices[0].get("change_pct", 0)) >= 1:
                    relevance_score += 4
            category = item.get("category", "")
            if category in ("M&A", "실적", "공시", "정책·규제"):
                relevance_score += 5
            relevance_score = min(25, relevance_score)

            total = coverage_score + keyword_score + source_score + relevance_score

            results.append({
                "title": title,
                "source": source,
                "url": item.get("url", ""),
                "score": round(total, 1),
                "coverage_score": coverage_score,
                "keyword_score": keyword_score,
                "source_credibility_score": source_score,
                "market_relevance_score": relevance_score,
                "category": category,
                "stock_code": stock_code,
                "stock_name": item.get("stock_name", ""),
                "impact_reason": "규칙 기반 점수",
                "coverage_count": coverage_count,
                "coverage_sources": item.get("coverage_sources", [source]),
                "news_id": item.get("id"),
            })
        return results

    @staticmethod
    def _compute_keyword_score(text: str) -> int:
        text_lower = text.lower()
        for score, keywords in HIGH_IMPACT_KEYWORDS:
            for kw in keywords:
                if kw.lower() in text_lower:
                    return score
        return 2  # 키워드 미매칭 시 최소 점수

    def _save_news_rankings(self, run_date: str, ranked: list[dict]):
        for r in ranked:
            sources = r.get("coverage_sources", [])
            sources_str = ",".join(sources) if isinstance(sources, list) else str(sources)
            self.repo.insert_news_ranking(
                run_date=run_date,
                rank=r.get("rank", 0),
                news_id=r.get("news_id"),
                title=r.get("title", ""),
                source=r.get("source", ""),
                url=r.get("url", ""),
                score=r.get("score", 0),
                coverage_score=r.get("coverage_score", 0),
                keyword_score=r.get("keyword_score", 0),
                source_credibility_score=r.get("source_credibility_score", 0),
                market_relevance_score=r.get("market_relevance_score", 0),
                category=r.get("category", ""),
                stock_code=r.get("stock_code", "") or None,
                stock_name=r.get("stock_name", ""),
                impact_reason=r.get("impact_reason", ""),
                coverage_count=r.get("coverage_count", 1),
                coverage_sources=sources_str,
            )
