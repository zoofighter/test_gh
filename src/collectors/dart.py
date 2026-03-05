import logging
from datetime import datetime, timedelta

import requests

from src.collectors.base import BaseCollector, NewsItem

logger = logging.getLogger(__name__)

DART_API_URL = "https://opendart.fss.or.kr/api"


class DartCollector(BaseCollector):
    source_name = "dart"

    def collect(self) -> list[NewsItem]:
        dart_cfg = self.config.get("collectors", {}).get("dart", {})
        if not dart_cfg.get("enabled", True):
            return []

        api_key = self.config.get("dart", {}).get("api_key", "")
        if not api_key or api_key == "63a05482f88e2c668cf7c85915841f830951060b":
            logger.warning("[DART] API 키가 설정되지 않았습니다. config.yaml을 확인하세요.")
            return []

        items = []
        today = datetime.now()
        bgn_de = (today - timedelta(days=1)).strftime("%Y%m%d")
        end_de = today.strftime("%Y%m%d")

        # 주요 공시 유형별 수집
        for pblntf_ty in ["A", "B", "C", "D", "E", "F", "G", "H", "I"]:
            items.extend(self._fetch_disclosures(api_key, bgn_de, end_de, pblntf_ty))

        logger.info(f"[DART] 수집 완료: {len(items)}건")
        return items

    def _fetch_disclosures(self, api_key: str, bgn_de: str, end_de: str,
                           pblntf_ty: str) -> list[NewsItem]:
        items = []
        try:
            resp = requests.get(
                f"{DART_API_URL}/list.json",
                params={
                    "crtfc_key": api_key,
                    "bgn_de": bgn_de,
                    "end_de": end_de,
                    "pblntf_ty": pblntf_ty,
                    "page_count": 100,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "000":
                return []

            for item in data.get("list", []):
                corp_code = item.get("corp_code", "")
                stock_code = item.get("stock_code", "").strip()
                corp_name = item.get("corp_name", "")
                report_nm = item.get("report_nm", "")
                rcept_no = item.get("rcept_no", "")
                rcept_dt = item.get("rcept_dt", "")

                if not stock_code:
                    continue

                url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                pub_date = f"{rcept_dt[:4]}-{rcept_dt[4:6]}-{rcept_dt[6:8]}" if len(rcept_dt) == 8 else rcept_dt

                items.append(NewsItem(
                    source="dart",
                    title=f"[공시] {corp_name} - {report_nm}",
                    url=url,
                    content=report_nm,
                    published_at=pub_date,
                    stock_code=stock_code,
                    stock_name=corp_name,
                    category="공시",
                    extra={"corp_code": corp_code, "rcept_no": rcept_no},
                ))
        except Exception as e:
            logger.warning(f"[DART] 공시 수집 실패 (유형 {pblntf_ty}): {e}")
        return items
