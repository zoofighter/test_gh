"""뉴스 영향력 추적 - 뉴스 발행 후 실제 주가 변동 측정"""

import logging

from src.database.repository import Repository

logger = logging.getLogger(__name__)


class ImpactTracker:
    def __init__(self, repo: Repository):
        self.repo = repo

    def calculate_impacts(self):
        """stock_code가 있는 뉴스 랭킹에 대해 실제 주가 변동 계산"""
        rankings = self.repo.get_latest_news_rankings()
        if not rankings:
            logger.info("[ImpactTracker] 뉴스 랭킹 데이터 없음")
            return

        calculated = 0
        skipped = 0

        for r in rankings:
            stock_code = r.get("stock_code")
            if not stock_code:
                continue

            nr_id = r.get("id")
            if self.repo.impact_exists(nr_id):
                skipped += 1
                continue

            pub_date = r["run_date"][:10]
            news_id = r.get("news_id")
            predicted_score = r.get("score", 0)

            base_price = self.repo.get_price_on_date(stock_code, pub_date)
            if not base_price:
                continue

            # +1일, +7일, +30일 후 종가 조회
            price_1d = self.repo.get_price_after_date(stock_code, pub_date, 1)
            price_1w = self.repo.get_price_after_date(stock_code, pub_date, 7)
            price_1m = self.repo.get_price_after_date(stock_code, pub_date, 30)

            # 변동률 계산
            change_1d = self._calc_change(base_price, price_1d)
            change_1w = self._calc_change(base_price, price_1w)
            change_1m = self._calc_change(base_price, price_1m)

            self.repo.insert_news_impact(
                news_ranking_id=nr_id,
                news_id=news_id,
                stock_code=stock_code,
                published_date=pub_date,
                base_price=base_price,
                price_1d=price_1d,
                price_1w=price_1w,
                price_1m=price_1m,
                change_pct_1d=change_1d,
                change_pct_1w=change_1w,
                change_pct_1m=change_1m,
                predicted_score=predicted_score,
            )
            calculated += 1

        if skipped:
            logger.info(f"[ImpactTracker] {skipped}건 기존 데이터 건너뜀")
        logger.info(f"[ImpactTracker] {calculated}건 영향력 계산 완료")

    @staticmethod
    def _calc_change(base: float, target: float) -> float | None:
        if target is None or base is None or base == 0:
            return None
        return round(((target - base) / base) * 100, 2)
