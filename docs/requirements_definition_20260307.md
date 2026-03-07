# 주식 랭킹 뉴스 시스템 - 요건정의서

> 작성일: 2026-03-07
> 프로젝트: `a_0305/`
> 참조 구현체: `0224_a/` (31개 모듈, 2,911줄)

---

## 1. 프로젝트 개요

### 1.1 목적

주식 시장 뉴스를 다수의 소스에서 자동 수집하고, LLM 기반 랭킹 엔진을 통해 **주가 영향력이 높은 뉴스를 순위화**하여 개인 투자자에게 제공하는 파이썬 시스템.

### 1.2 대상 시장

| 항목 | 내용 |
|------|------|
| 국내 | KOSPI / KOSDAQ |
| 해외 | NYSE / NASDAQ |
| 종목 범위 | `config.yaml` 관심 종목 + 뉴스 본문 자동 추출 |

### 1.3 핵심 가치

- 다양한 소스의 뉴스를 **단일 파이프라인**으로 통합
- LLM 기반 영향력 점수(0~100점)로 **정량적 랭킹** 제공
- 뉴스 발행 후 실제 주가 변동을 추적하여 **예측 정확도 검증**

---

## 2. 구현 현황 요약

### 2.1 단계별 진행 상황

| 단계 | 내용 | 상태 | 완료일 |
|------|------|------|--------|
| 1단계 | 뉴스 수집 모듈 (8개 소스) | 완료 | 2026-03-05 |
| 2단계 | DB 스키마 및 저장 모듈 (8개 테이블) | 완료 | 2026-03-05 |
| 3단계 | 전처리 파이프라인 (중복제거/종목매핑/분류) | 완료 | 2026-03-06 |
| 4단계 | 주가 데이터 수집 (한국/미국) | 완료 | 2026-03-06 |
| 5단계 | LLM 랭킹 엔진 + 규칙 기반 폴백 | 완료 | 2026-03-06 |
| 6단계 | 뉴스 영향력 추적 (1일/1주/1월) | 완료 | 2026-03-06 |
| 7단계 | 출력 모듈 (CLI/CSV/텔레그램) | 미구현 | - |
| 8단계 | 스케줄러 / 대시보드 / REST API | 미구현 | - |

### 2.2 코드 규모

| 항목 | 수치 |
|------|------|
| Python 모듈 | 19개 |
| 설정/의존성 파일 | 2개 (config.yaml, requirements.txt) |
| 총 코드 라인 | ~3,077줄 |

---

## 3. 시스템 아키텍처

### 3.1 전체 파이프라인

```
python main.py [옵션]
       │
       ▼
┌──────────────────┐
│  1. 뉴스 수집     │  8개 소스 → List[NewsItem]
│  src/collectors/  │
└───────┬──────────┘
        ▼
┌──────────────────┐
│  2. 전처리        │  중복제거 → 종목매핑 → 카테고리 분류
│  src/preprocessor/│
└───────┬──────────┘
        ▼
┌──────────────────┐
│  3. DB 저장       │  종목 등록(FK) → 뉴스 저장(URL 중복체크)
│  src/database/    │
└───────┬──────────┘
        ▼
┌──────────────────┐
│  4. 주가 수집     │  pykrx(한국) + yfinance(미국), 35일치
│  src/stock_data/  │
└───────┬──────────┘
        ▼
┌──────────────────┐
│  5. 랭킹 분석     │  LLM 기반 스코어링 → 규칙 기반 폴백
│  src/ranking/     │
└───────┬──────────┘
        ▼
┌──────────────────┐
│  6. 영향력 추적   │  뉴스 발행 후 1일/1주/1월 주가 변동
│  src/ranking/     │
└───────┬──────────┘
        ▼
┌──────────────────┐
│  7. 결과 출력     │  터미널 테이블 + DB 통계
│  main.py          │
└──────────────────┘
```

### 3.2 프로젝트 파일 구조

```
a_0305/
├── main.py                           # CLI 진입점
├── config.yaml                       # 전체 설정
├── requirements.txt                  # 의존성
├── data/
│   └── stock_ranking.db              # SQLite DB
├── docs/                             # 문서
└── src/
    ├── collectors/                    # 뉴스 수집 (9개 파일)
    │   ├── base.py                   #   NewsItem + BaseCollector
    │   ├── naver.py                  #   네이버 금융뉴스
    │   ├── dart.py                   #   DART 공시 API
    │   ├── yahoo.py                  #   Yahoo Finance
    │   ├── rss.py                    #   RSS (한경/매경)
    │   ├── google_news.py            #   Google News RSS
    │   ├── reddit.py                 #   Reddit JSON API
    │   ├── twitter.py                #   Twitter/Nitter (비활성)
    │   └── naver_discussion.py       #   네이버 토론방 (비활성)
    ├── database/                      # DB 계층
    │   ├── models.py                 #   스키마 (8 테이블)
    │   └── repository.py             #   Repository CRUD
    ├── preprocessor/                  # 전처리
    │   ├── dedup.py                  #   중복 제거
    │   ├── kr_stock_dict.py          #   한국 종목 사전 (pykrx)
    │   ├── stock_mapper.py           #   종목 매핑
    │   └── categorizer.py            #   카테고리 분류
    ├── ranking/                       # 랭킹 엔진
    │   ├── engine.py                 #   RankingEngine + NewsRankingEngine
    │   ├── impact_tracker.py         #   영향력 추적
    │   └── prompts.py                #   LLM 프롬프트
    └── stock_data/                    # 주가 데이터
        ├── kr_stock.py               #   pykrx (한국)
        └── us_stock.py               #   yfinance (미국)
```

---

## 4. 기능 요건 상세

### 4.1 뉴스 수집 (src/collectors/)

#### 4.1.1 공통 데이터 구조

```python
@dataclass
class NewsItem:
    source: str          # 수집 소스 (naver, dart, yahoo 등)
    title: str           # 기사 제목
    url: str             # 기사 URL
    content: str         # 본문/요약
    published_at: str    # 발행 시각
    stock_code: str      # 종목 코드 (전처리 단계에서 채움)
    stock_name: str      # 종목명 (전처리 단계에서 채움)
    category: str        # 카테고리 (전처리 단계에서 채움)
    extra: dict          # 메타데이터 (coverage_count, coverage_sources)
```

#### 4.1.2 수집기별 요건

| # | 수집기 | 소스 | 수집 방식 | 신뢰도 | 상태 |
|---|--------|------|----------|--------|------|
| 1 | NaverCollector | 네이버 금융뉴스 | HTML 스크레이핑 | 15점 | 활성 |
| 2 | DartCollector | DART 공시 | REST API (API 키 필요) | 25점 | 활성 |
| 3 | YahooCollector | Yahoo Finance | yfinance 라이브러리 | 18점 | 활성 |
| 4 | RssCollector | 한국경제/매일경제 | feedparser RSS | 18점 | 활성 |
| 5 | GoogleNewsCollector | Google News | RSS (토픽+검색) | 14점 | 활성 |
| 6 | RedditCollector | Reddit | JSON API | 8점 | 활성 |
| 7 | TwitterCollector | Twitter/X | Nitter 프록시 | 8점 | 비활성 |
| 8 | NaverDiscussionCollector | 네이버 토론방 | HTML 스크레이핑 | 6점 | 비활성 |

#### 4.1.3 수집 결과 (테스트 기준)

- naver: 45건, yahoo: 50건, rss: 50건, google_news: 108건, reddit: 44건
- **총 297건** 수집 → 전처리 후 **257건** (40건 중복 제거)

---

### 4.2 전처리 파이프라인 (src/preprocessor/)

#### 4.2.1 중복 제거 (dedup.py)

| 항목 | 내용 |
|------|------|
| 알고리즘 | `difflib.SequenceMatcher` 제목 유사도 비교 |
| 임계값 | 80% 이상 유사 → 중복 판정 |
| 출력 메타데이터 | `coverage_count` (보도 매체 수), `coverage_sources` (매체 목록) |

#### 4.2.2 종목 매핑 (stock_mapper.py)

| 우선순위 | 매칭 방식 | 설명 |
|----------|----------|------|
| 1순위 | 종목명 매칭 | DB 종목 + pykrx 한국 전종목 사전 (긴 이름 우선) |
| 2순위 | 코드 패턴 | 6자리 숫자 → 한국 종목코드 |
| 3순위 | 티커 패턴 | 1~5자 대문자 영문 → 미국 티커 |

- pykrx 매칭 시 DB 자동 등록 (KOSPI/KOSDAQ)
- 한국 종목 사전 (`kr_stock_dict.py`): 모듈 레벨 캐시, 프로세스당 1회 로드

#### 4.2.3 카테고리 분류 (categorizer.py)

| 카테고리 | 주요 키워드 (한/영) |
|----------|-------------------|
| 실적 | 실적, 영업이익, 매출 / earnings, revenue |
| 공시 | 공시, 유상증자 / disclosure |
| M&A | 인수, 합병 / merger, acquisition |
| 신사업 | 신사업, 신규진출 / new business |
| 거시경제 | 금리, 환율, GDP / interest rate |
| 섹터이슈 | 반도체, 배터리 / semiconductor |
| 수급 | 외국인, 기관, 공매도 / short selling |
| 정책·규제 | 규제, 정책 / regulation, tariff |

- 이미 카테고리 할당된 항목(DART 공시 등)은 건너뜀
- 257건 중 122건 분류 완료

---

### 4.3 데이터베이스 (src/database/)

#### 4.3.1 DB 엔진

- **SQLite** (향후 PostgreSQL 마이그레이션 경로 확보)
- FK 제약 활성화 (`PRAGMA foreign_keys = ON`)
- 30일 초과 데이터 자동 정리 (`cleanup_old_data`)

#### 4.3.2 테이블 스키마 (8개)

| 테이블 | 용도 | 주요 컬럼 |
|--------|------|----------|
| `stocks` | 종목 마스터 | code(PK), name, market, sector |
| `news` | 수집 뉴스 | id(PK), source, title, url, content, published_at, category, stock_code(FK) |
| `stock_prices` | 일봉 주가 | stock_code(FK)+date(PK), close, volume, change_pct |
| `rankings` | 종목 랭킹 | run_date, rank, stock_code(FK), score, summary |
| `ranking_news` | 랭킹-뉴스 M:N | ranking_id(FK), news_id(FK) |
| `news_rankings` | 뉴스별 랭킹 | run_date, rank, news_id(FK), score, impact_reason |
| `news_impact` | 영향력 추적 | news_ranking_id(FK), stock_code(FK), price_1d/1w/1m, change_pct_1d/1w/1m |
| `scheduler_log` | 실행 로그 | run_id, status, news_count, duration_sec |

#### 4.3.3 Repository 패턴

- 단일 `Repository` 클래스로 모든 CRUD 캡슐화
- URL 기반 뉴스 중복 체크 (`news_exists`)
- 종목 코드 형식으로 시장 자동 판별 (6자리 → KOSPI/KOSDAQ, 영문 → NYSE)

---

### 4.4 주가 데이터 수집 (src/stock_data/)

| 항목 | 한국 주식 | 미국 주식 |
|------|----------|----------|
| 라이브러리 | pykrx | yfinance |
| 시장 | KOSPI / KOSDAQ | NYSE / NASDAQ |
| 데이터 | 일봉 OHLCV | 일봉 OHLCV |
| 기간 | 최근 35일 | 최근 35일 |
| 저장 | `repo.upsert_price()` | `repo.upsert_price()` |
| 에러 처리 | 종목별 예외 격리 | 종목별 예외 격리 |

---

### 4.5 랭킹 엔진 (src/ranking/)

#### 4.5.1 2단계 랭킹 아키텍처

| 레벨 | 엔진 | 대상 | 배치 크기 |
|------|------|------|----------|
| 뉴스 랭킹 | NewsRankingEngine | 개별 뉴스 기사 | 20건/배치 |
| 종목 랭킹 | RankingEngine | 종목 단위 집계 | 10종목/배치 |

#### 4.5.2 스코어링 (0~100점)

| 평가 항목 (각 0~25점) | 산출 방식 |
|----------------------|----------|
| **Coverage Score** | `min(25, coverage_count * 8)` |
| **Keyword Score** | 5단계 키워드 티어 매칭 (M&A=25, 실적=20, 공시=15, 금리=10, AI=5) |
| **Source Credibility** | 소스별 고정 점수 (DART:25, Yahoo:18, RSS:18, Naver:15, ...) |
| **Market Relevance** | 종목 언급(+12) + 주가 변동률(+4~8) + 카테고리 프리미엄(+5) |

#### 4.5.3 LLM 연동

| 항목 | 내용 |
|------|------|
| 1차 | LM Studio (로컬, `localhost:1234`, OpenAI 호환 API) |
| 2차 | 온라인 LLM (OpenAI/Anthropic, config에서 활성화) |
| 3차 (폴백) | 규칙 기반 랭킹 (`뉴스수*15 + 주가변동*2 + 거래량*0.5`) |
| 프롬프트 | `prompts.py`에 시스템/유저 프롬프트 정의, JSON 출력 |
| 온도 | 0.1 (결정론적 출력) |

#### 4.5.4 영향력 추적 (impact_tracker.py)

| 항목 | 내용 |
|------|------|
| 추적 시점 | 뉴스 발행일 기준 1일 후 / 7일 후 / 30일 후 |
| 계산 | `((target_price - base_price) / base_price) * 100` |
| 저장 | `news_impact` 테이블, 이미 계산된 건은 스킵 |
| 용도 | 랭킹 예측 정확도 사후 검증 |

---

### 4.6 CLI 실행 옵션

```bash
python main.py                  # 전체 파이프라인 실행
python main.py -c custom.yaml   # 별도 설정 파일 사용
python main.py -v               # 상세 로그 (DEBUG)
python main.py --no-collect     # 뉴스 수집 건너뛰기
python main.py --no-save        # DB 저장 건너뛰기
python main.py --no-price       # 주가 수집 건너뛰기
python main.py --no-rank        # 랭킹 분석 건너뛰기
python main.py --stats          # DB 현황 조회만
```

---

## 5. 설정 파일 (config.yaml)

### 5.1 주요 설정 항목

```yaml
# DART API 키
dart:
  api_key: "YOUR_DART_API_KEY"

# 수집기별 활성화 및 파라미터
collectors:
  naver: { enabled: true, max_pages: 3 }
  dart:  { enabled: true }
  yahoo: { enabled: true }
  rss:   { enabled: true, feeds: [...] }
  google_news: { enabled: true, feeds: [kr_business, us_business] }
  reddit: { enabled: true, subreddits: [stocks, wallstreetbets], min_score: 50 }
  twitter: { enabled: false }
  naver_discussion: { enabled: false }

# 관심 종목
watchlist:
  kr: ["005930", "000660"]     # 삼성전자, SK하이닉스
  us: ["AAPL", "TSLA"]

# 랭킹 파라미터
ranking:
  top_n: 30
  news_batch_size: 20
  weights: { coverage: 25, keyword: 25, volume: 25, source: 25 }

# LLM 설정
lm_studio:
  base_url: "http://localhost:1234/v1"
  model: "local-model"
  temperature: 0.1

# DB
database:
  path: "data/stock_ranking.db"
```

---

## 6. 기술 스택 및 의존성

| 영역 | 기술 | 용도 |
|------|------|------|
| 언어 | Python 3.10+ | - |
| HTTP | requests >= 2.31 | 뉴스 수집 |
| HTML 파싱 | beautifulsoup4 >= 4.12 | 스크레이핑 |
| RSS | feedparser >= 6.0 | RSS 수집 |
| 한국 주가 | pykrx >= 1.0 | KOSPI/KOSDAQ 주가 |
| 미국 주가 | yfinance >= 0.2.36 | NYSE/NASDAQ 주가 |
| LLM | langchain-openai >= 0.1, langchain-core >= 0.2 | 랭킹 엔진 |
| 설정 | pyyaml >= 6.0 | config.yaml 파싱 |
| DB | sqlite3 (내장) | 데이터 저장 |

---

## 7. 설계 원칙

| 원칙 | 적용 내용 |
|------|----------|
| **모듈 독립성** | 각 컴포넌트(수집/전처리/랭킹)가 독립적으로 교체 가능 |
| **폴백 전략** | LM Studio → 온라인 LLM → 규칙 기반 (항상 결과 보장) |
| **비용 최적화** | 무료 API만 사용, 로컬 LLM으로 API 비용 제거 |
| **프라이버시** | 로컬 LLM 우선으로 뉴스/주가 데이터 외부 전송 최소화 |
| **투명한 스코어링** | 4개 항목별 점수 분해로 랭킹 근거 명시 |
| **에러 격리** | 수집기/종목별 예외 처리로 단일 실패가 전체에 영향 없음 |
| **Repository 패턴** | DB 접근 캡슐화, PostgreSQL 마이그레이션 용이 |

---

## 8. 미구현 기능 및 향후 로드맵

### 8.1 미구현 모듈

| 모듈 | 설명 | 우선순위 | 참조 구현 |
|------|------|----------|----------|
| CLI 출력 (rich) | 컬러 테이블 포맷 출력 | 높음 | `0224_a/src/output/cli.py` |
| CSV 내보내기 | 한글 컬럼명 CSV 저장 | 높음 | `0224_a/src/output/csv_export.py` |
| 텔레그램 알림 | 랭킹 결과 봇 전송 | 중간 | `0224_a/src/output/telegram_bot.py` |
| 거래량 경보 | 비정상 거래량 감지 (3배+) | 중간 | `0224_a/src/stock_data/volume_alert.py` |
| 스케줄러 | APScheduler 자동 실행 (장전/장후) | 중간 | `0224_a/scheduler.py` |
| Streamlit 대시보드 | 웹 기반 랭킹/이력 시각화 | 낮음 | `0224_a/dashboard.py` |
| FastAPI REST API | 18개 엔드포인트 API 서버 | 낮음 | `0224_a/api.py` |

### 8.2 추가 뉴스 소스 확장 (Phase 4)

#### Phase 4A - 공시·리서치 강화

| 소스 | 수집 방식 | 신뢰도 | 우선순위 |
|------|----------|--------|---------|
| SEC EDGAR | REST API | 25점 | ★★★ |
| KRX KIND | 스크레이핑/OpenAPI | 25점 | ★★★ |
| 네이버 리서치 | 스크레이핑 | 20점 | ★★★ |
| PR Newswire/Business Wire | RSS | 22점 | ★★★ |

#### Phase 4B - 뉴스 소스 다양화

| 소스 | 수집 방식 | 신뢰도 | 우선순위 |
|------|----------|--------|---------|
| Finviz | 스크레이핑 | 16점 | ★★★ |
| 이데일리/머니투데이 | RSS/스크레이핑 | 16점 | ★★☆ |
| MarketWatch/CNBC | RSS | 16점 | ★★☆ |
| StockTwits | REST API | 8점 | ★★☆ |

#### Phase 4C - 대체 데이터

| 소스 | 수집 방식 | 신뢰도 | 우선순위 |
|------|----------|--------|---------|
| 38커뮤니케이션 | 스크레이핑 | 10점 | ★★☆ |
| Seeking Alpha | RSS/스크레이핑 | 14점 | ★★☆ |
| 텔레그램 채널 | Telethon API | 6점 | ★☆☆ |
| YouTube 자막 | youtube-transcript-api | - | ★☆☆ |

---

## 9. 데이터 흐름 예시

```
[수집]  네이버 금융뉴스에서 "삼성전자, Q4 매출 전년대비 50% 증가" 기사 수집
         ↓
[중복제거] 동일 기사가 Yahoo, Google News에서도 수집됨
         → coverage_count: 3, coverage_sources: [naver, yahoo, google_news]
         ↓
[종목매핑] "삼성전자" → stock_code: "005930", stock_name: "삼성전자"
         ↓
[분류]   키워드 "매출" 매칭 → category: "실적"
         ↓
[DB 저장] news 테이블 INSERT (URL 중복 체크 통과)
         ↓
[주가수집] pykrx로 005930 최근 35일 OHLCV 저장
         ↓
[랭킹]   LLM 스코어링:
         - coverage_score: 20 (3개 소스)
         - keyword_score: 20 (매출 → 실적 Tier 2)
         - source_credibility: 15 (naver 기준)
         - market_relevance: 22 (종목 언급 + 카테고리 프리미엄)
         → 총점: 77점, 순위: 3위
         ↓
[영향추적] 발행일 종가 70,000원 기준
         → 1일 후: 71,400원 (+2.0%)
         → 1주 후: 73,500원 (+5.0%)
         → 1월 후: 77,000원 (+10.0%)
```

---

## 10. 비기능 요건

| 항목 | 내용 |
|------|------|
| 데이터 보관 | 30일 (자동 정리) |
| 수집 주기 | Phase 1: 수동 실행 / 향후: 장전 08:30 + 장후 16:00 |
| Rate Limit | 네이버 0.5초 간격, Reddit 2초 간격 등 소스별 준수 |
| LLM 온도 | 0.1 (일관된 랭킹 결과 보장) |
| 에러 복구 | 개별 수집기/종목 실패 시 로그 후 계속 진행 |
| 유료 API | 사용하지 않음 (전량 무료 소스) |

---

## 부록 A. DB 스키마 관계도

```
┌──────────┐       ┌──────────┐       ┌────────────────┐
│  stocks  │◄──FK──│   news   │──FK──►│  news_rankings │
│  (종목)  │       │  (뉴스)  │       │  (뉴스랭킹)     │
└────┬─────┘       └──────────┘       └───────┬────────┘
     │                                        │
     │  ┌──────────────┐              ┌───────▼────────┐
     ├──│ stock_prices  │              │  news_impact   │
     │  │ (주가 데이터)  │              │  (영향력 추적)  │
     │  └──────────────┘              └────────────────┘
     │
     │  ┌──────────────┐    ┌────────────────┐
     └──│  rankings    │◄──►│  ranking_news  │
        │ (종목랭킹)    │    │  (M:N 매핑)    │
        └──────────────┘    └────────────────┘

        ┌──────────────┐
        │ scheduler_log│
        │ (실행 로그)   │
        └──────────────┘
```

---

## 부록 B. 출력 예시

```
════════════════════════════════════════════════════════════════
 뉴스 영향력 랭킹 Top 30
════════════════════════════════════════════════════════════════
  1. [ 85.0점] [dart] [005930] 삼성전자 (공시)
     삼성전자, 대규모 자본확충 결정
     사유: 핵심 공시 + 중복보도 5매체

  2. [ 77.0점] [naver] [005930] 삼성전자 (실적)
     삼성전자, Q4 매출 전년대비 50% 증가
     사유: 매출 실적 + 3개 매체 보도

  3. [ 65.5점] [yahoo] [AAPL] AAPL (실적)
     Apple reports record Q1 revenue
     사유: Earnings beat + high source credibility
════════════════════════════════════════════════════════════════
```
