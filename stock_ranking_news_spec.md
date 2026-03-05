# 주식 랭킹 뉴스 시스템 - 요건 정의서

> 작성일: 2026-02-24


## 1. 프로젝트 개요

주식 시장의 뉴스를 자동 수집하고, **LangChain + LM Studio(로컬 LLM)** 기반 랭킹 로직을 통해 개별 기업 주가에 영향이 큰 뉴스를 순위화하여 제공하는 파이썬 시스템.

---

## 2. 확정 요건

### 2.1 대상 시장

| 항목 | 결정 사항 |
|------|----------|
| 타겟 시장 | **국내(KOSPI/KOSDAQ) + 미국(NYSE/NASDAQ)** |
| 종목 범위 | 관심 종목 설정 가능 (config.yaml), 뉴스에서 자동 추출도 지원 |

### 2.2 뉴스 소스 및 수집

| 항목 | 결정 사항 |
|------|----------|
| 뉴스 소스 (Phase 1) | **네이버 금융뉴스, DART 공시, Yahoo Finance, RSS(한경/매경)** |
| 유료 API | **무료만 사용** |
| SNS/커뮤니티 | Phase 2에서 추가 (트위터(X), 네이버 종목토론방) |
| 수집 주기 | **장전·장후 1일 2회** (Phase 1은 수동 실행) |
| 크롤링 정책 | **공개 API, RSS, 스크레이핑 전부 사용** |

### 2.3 뉴스 분석 및 랭킹 로직

| 항목 | 결정 사항 |
|------|----------|
| 감성분석(Sentiment) | **사용하지 않음** |
| 랭킹 판단 기준 | ① 뉴스 중복 보도량(0~25점) ② 키워드 가중치(0~25점) ③ 주가/거래량 변동(0~25점) ④ 뉴스 소스 신뢰도(0~25점) |
| 랭킹 엔진 | **LangChain + LM Studio** (OpenAI 호환 API, localhost:1234) |
| 종목 매핑 | 기사 본문에서 종목명·코드 추출 + 종목 태그 소스 병행 |
| 중복 제거 | 제목 유사도 80% 이상이면 동일 건 |
| 카테고리 분류 | 실적/공시/M&A/신사업/거시경제/섹터이슈/수급/정책·규제 |
| 폴백 | LLM 실패 시 뉴스 수+주가변동 기반 간단 랭킹 자동 적용 |

### 2.4 주가 데이터

| 항목 | 결정 사항 |
|------|----------|
| 시세 단위 | **일봉 + 종가** (실시간 불필요) |
| 국내 데이터 소스 | **pykrx** |
| 미국 데이터 소스 | **yfinance** |

### 2.5 기술 스택

| 항목 | 결정 사항 |
|------|----------|
| 언어 | Python 3.10+ |
| LLM | **LM Studio** (로컬 실행, OpenAI 호환) |
| 프레임워크 | LangChain + langchain-openai |
| 데이터 저장소 | **SQLite** → 추후 PostgreSQL |
| 스케줄러 | **1차: 수동 실행** → 추후 추가 |
| 출력 | **CLI (rich 테이블) + CSV 파일** |

### 2.6 결과물

| 항목 | 결정 사항 |
|------|----------|
| 출력 형태 | CLI 터미널 테이블 + CSV 파일 저장 |
| 랭킹 표시 수 | Top 20 (config에서 변경 가능) |
| 과거 이력 조회 | 최근 30일 |
| 데이터 보관 | 30일 후 자동 정리 |

---

## 3. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────┐
│              python main.py (수동 실행)                │
│               (추후 스케줄러 자동화)                     │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │     뉴스 수집 모듈        │
          │  src/collectors/         │
          │                         │
          │  - naver.py  (네이버)    │
          │  - dart.py   (DART공시)  │
          │  - yahoo.py  (Yahoo)    │
          │  - rss.py    (한경/매경) │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │    전처리 모듈            │
          │  src/preprocessor/       │
          │                         │
          │  - dedup.py     (중복제거)│
          │  - stock_mapper.py (매핑)│
          │  - categorizer.py (분류) │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │   주가 데이터 모듈        │
          │  src/stock_data/         │
          │                         │
          │  - kr_stock.py  (pykrx)  │
          │  - us_stock.py  (yfinance)│
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │  LangChain 랭킹 엔진     │
          │  src/ranking/            │
          │                         │
          │  - prompts.py (프롬프트)  │
          │  - engine.py  (랭킹실행)  │
          │  → LM Studio 로컬 LLM    │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │   저장 (SQLite)          │
          │  src/database/           │
          │                         │
          │  - models.py  (스키마)    │
          │  - repository.py (CRUD)  │
          │  → data/stock_ranking.db │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │   결과 출력 모듈          │
          │  src/output/             │
          │                         │
          │  - cli.py    (터미널)     │
          │  - csv_export.py (CSV)   │
          │  → data/exports/         │
          └─────────────────────────┘
```

---

## 4. DB 스키마

| 테이블 | 설명 |
|--------|------|
| `stocks` | 종목 마스터 (code, name, market, sector) |
| `news` | 수집된 뉴스 (source, title, url, content, published_at, category, stock_code) |
| `stock_prices` | 주가 데이터 (stock_code, date, close, volume, change_pct) |
| `rankings` | 랭킹 결과 (run_date, rank, stock_code, score, summary 등) |
| `ranking_news` | 랭킹-뉴스 연결 (ranking_id, news_id) |

---

## 5. 프로젝트 파일 구조

```

├── config.yaml.example          # 설정 예시
├── requirements.txt             # 의존성
├── main.py                      # 메인 실행 진입점
├── dashboard.py                 # Streamlit 웹 대시보드
├── api.py                       # FastAPI REST API 서버
├── scheduler.py                 # APScheduler 자동 실행
├── src/
│   ├── collectors/              # 뉴스 수집 (6개 소스)
│   │   ├── base.py              #   BaseCollector 추상 클래스
│   │   ├── naver.py             #   네이버 금융뉴스
│   │   ├── dart.py              #   DART 공시 API
│   │   ├── yahoo.py             #   Yahoo Finance
│   │   ├── rss.py               #   RSS 피드 (한경/매경)
│   │   ├── twitter.py           #   트위터(X) via Nitter
│   │   └── naver_discussion.py  #   네이버 종목토론방
│   ├── preprocessor/            # 전처리
│   │   ├── dedup.py             #   중복 뉴스 제거
│   │   ├── stock_mapper.py      #   뉴스→종목 매핑
│   │   └── categorizer.py       #   카테고리 분류
│   ├── stock_data/              # 주가 데이터
│   │   ├── kr_stock.py          #   pykrx (국내)
│   │   ├── us_stock.py          #   yfinance (미국)
│   │   └── volume_alert.py      #   거래량 급증 감지
│   ├── ranking/                 # LangChain 랭킹 엔진
│   │   ├── prompts.py           #   프롬프트 + 가중치 시스템
│   │   └── engine.py            #   랭킹 체인 실행
│   ├── database/                # DB
│   │   ├── models.py            #   테이블 정의 + 초기화
│   │   └── repository.py        #   CRUD 함수
│   └── output/                  # 출력
│       ├── cli.py               #   터미널 출력 (rich)
│       ├── csv_export.py        #   CSV 저장
│       └── telegram_bot.py      #   텔레그램 봇 알림
└── data/
    ├── stock_ranking.db         # SQLite DB (자동 생성)
    └── exports/                 # CSV 출력 디렉토리
```

---

## 6. 실행 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 설정 파일 생성
cp config.yaml.example config.yaml
# config.yaml에 DART API 키, LM Studio 설정, 텔레그램 토큰 등 입력

# 3. LM Studio 실행
# LM Studio에서 모델 로드 후 서버 시작 (localhost:1234)

# 4. 수동 실행
python main.py                  # 전체 파이프라인 실행
python main.py -v               # 상세 로그 출력
python main.py --no-collect     # 뉴스 수집 건너뛰기 (DB 기존 데이터 사용)
python main.py --no-price       # 주가 수집 건너뛰기
python main.py --history 30     # 최근 30일 랭킹 이력 조회

# 5. Streamlit 대시보드
streamlit run dashboard.py

# 6. REST API 서버
uvicorn api:app --reload --port 8000
# Swagger 문서: http://localhost:8000/docs

# 7. 스케줄러 (장전 08:30 / 장후 16:00 자동 실행)
python scheduler.py
```

---

## 7. 개발 로드맵

### Phase 1 - MVP (완료)
- [x] 뉴스 수집기 4개 (네이버, DART, Yahoo Finance, RSS)
- [x] 기본 전처리 (중복 제거, 종목 매핑, 카테고리 분류)
- [x] LangChain + LM Studio 랭킹 엔진
- [x] SQLite 저장 (5개 테이블)
- [x] CLI 출력 (rich 테이블) + CSV 파일 저장
- [x] 과거 30일 이력 조회
- [x] LLM 실패 시 폴백 랭킹

### Phase 2 - 소스 확장 + UI (완료)
- [x] 뉴스 소스 추가 (트위터(X) via Nitter, 네이버 종목토론방)
- [x] Streamlit 웹 대시보드 (최신랭킹/이력/종목별뉴스/거래량급증 4개 뷰)
- [x] 텔레그램 봇 알림 (랭킹 + 거래량 급증)
- [x] 거래량 급증 감지 (평균 대비 N배 기준)

### Phase 3 - 자동화 + 고도화 (완료)
- [x] APScheduler 스케줄러 (장전 08:30 / 장후 16:00, 주말 제외)
- [x] 랭킹 로직 정교화 (config.yaml에서 4개 가중치 자유 조정)
- [x] FastAPI REST API 서버 (18개 엔드포인트, Swagger 문서 자동 생성)
- [ ] PostgreSQL 마이그레이션 (필요 시)
- [ ] 섹터별 분석 기능 (필요 시)

---

## 8. 추가 뉴스 수집 확장 방안

> 현재 8개 소스(네이버, DART, Yahoo, RSS, Twitter, 네이버토론방, Google News, Reddit) 외에 추가 가능한 뉴스 소스 목록

### 8.1 국내 시장 추가 소스

| # | 소스 | 수집 방식 | 데이터 유형 | API 키 | 우선순위 |
|---|------|----------|------------|--------|---------|
| K1 | **KRX KIND** (한국거래소 공시) | 스크레이핑 / OpenAPI | 기업 공시·IR 자료, 거래소 직접 공시 | 불필요 | ★★★ |
| K2 | **38커뮤니케이션** | 스크레이핑 | IPO 수요예측·공모주·신규상장 정보 | 불필요 | ★★☆ |
| K3 | **네이버 증권 리서치** | 스크레이핑 | 증권사 리포트 제목·목표가·투자의견 | 불필요 | ★★★ |
| K4 | **이데일리** | RSS / 스크레이핑 | 실시간 증권 뉴스, 시황 분석 | 불필요 | ★★☆ |
| K5 | **머니투데이** | RSS / 스크레이핑 | 증권·경제 뉴스 | 불필요 | ★★☆ |
| K6 | **연합인포맥스** | 스크레이핑 | 채권·외환·증권 종합 시황 | 불필요 | ★★☆ |
| K7 | **한국경제TV** | RSS / 스크레이핑 | 증권 영상 뉴스 텍스트, 속보 | 불필요 | ★☆☆ |
| K8 | **텔레그램 주식 채널** | Telethon API | 리딩방·속보 채널 메시지 | API 필요 | ★☆☆ |
| K9 | **디시인사이드 주식갤러리** | 스크레이핑 | 개인 투자자 심리·이슈 감지 | 불필요 | ★☆☆ |

### 8.2 미국 시장 추가 소스

| # | 소스 | 수집 방식 | 데이터 유형 | API 키 | 우선순위 |
|---|------|----------|------------|--------|---------|
| U1 | **SEC EDGAR** | REST API | 10-K, 10-Q, 8-K 공시 (미국판 DART) | 불필요 (User-Agent 필요) | ★★★ |
| U2 | **Finviz** | 스크레이핑 | 종목별 뉴스 헤드라인, 스크리너 | 불필요 | ★★★ |
| U3 | **StockTwits** | REST API | 종목별 투자자 의견·심리 지표 | 불필요 | ★★☆ |
| U4 | **PR Newswire / Business Wire** | RSS | 기업 공식 보도자료 (실적, 계약 등) | 불필요 | ★★★ |
| U5 | **Seeking Alpha** | RSS / 스크레이핑 | 심층 종목 분석, 실적 발표 요약 | 불필요 (제한적) | ★★☆ |
| U6 | **MarketWatch** | RSS | 시장 뉴스, 종목 뉴스, 경제 지표 | 불필요 | ★★☆ |
| U7 | **CNBC** | RSS | 주요 시장 뉴스, 속보 | 불필요 | ★★☆ |
| U8 | **Earnings Whispers** | 스크레이핑 | 실적 발표 일정, 어닝 서프라이즈 | 불필요 | ★☆☆ |

### 8.3 크로스마켓 / 대체 소스

| # | 소스 | 수집 방식 | 데이터 유형 | API 키 | 우선순위 |
|---|------|----------|------------|--------|---------|
| C1 | **Investing.com** | RSS / 스크레이핑 | 글로벌 시장 뉴스, 경제 캘린더 | 불필요 | ★★☆ |
| C2 | **Trading Economics** | 스크레이핑 | 경제 지표, 거시경제 이벤트 | 유료 API (스크레이핑 가능) | ★☆☆ |
| C3 | **YouTube 금융 채널** | youtube-transcript-api | 증권 유튜버 영상 자막 추출 | 불필요 | ★☆☆ |

### 8.4 추가 소스별 상세 설명

#### K1. KRX KIND (한국거래소 공시)
```
URL      : https://kind.krx.co.kr
수집방식  : OpenAPI 또는 HTML 스크레이핑
핵심 데이터:
  - 주요사항보고 (유상증자, 전환사채, 합병 등)
  - 공정공시 (매출액, 수주공시)
  - 거래소 자체 공시 (투자주의, 거래정지, 관리종목 지정)
차별점    : DART와 달리 거래소 직접 조치(투자경고, 거래정지 등)를 포함
구현 파일  : src/collectors/krx_kind.py
```

#### K3. 네이버 증권 리서치
```
URL      : https://finance.naver.com/research/
수집방식  : HTML 스크레이핑
핵심 데이터:
  - 증권사 리포트 제목
  - 투자의견 (매수/중립/매도)
  - 목표주가
  - 발행 증권사
차별점    : 기관 의견 변화를 추적 → 목표가 상향/하향이 주가에 직접 영향
구현 파일  : src/collectors/naver_research.py
```

#### U1. SEC EDGAR
```
URL      : https://efts.sec.gov/LATEST/search-index?q=...
API      : https://data.sec.gov/submissions/CIK{cik}.json
수집방식  : REST API (Full-Text Search API)
핵심 데이터:
  - 8-K (중요 사건 보고 - M&A, 경영진 변경, 실적 등)
  - 10-K / 10-Q (연간/분기 실적 보고서)
  - SC 13D/G (대량 보유 변동)
차별점    : 미국 공식 공시로 가장 높은 신뢰도, DART와 동급
헤더 필수  : User-Agent에 이메일 포함 필요
라이브러리 : sec-edgar-downloader, edgartools
구현 파일  : src/collectors/sec_edgar.py
```

#### U2. Finviz
```
URL      : https://finviz.com/quote.ashx?t={ticker}
수집방식  : HTML 스크레이핑 (뉴스 섹션)
핵심 데이터:
  - 종목별 뉴스 헤드라인 (여러 소스 통합)
  - 뉴스 발행 시간
  - 원문 링크
차별점    : 여러 뉴스 소스를 종목 단위로 통합 제공
라이브러리 : finvizfinance
구현 파일  : src/collectors/finviz.py
```

#### U4. PR Newswire / Business Wire
```
RSS 피드:
  - PR Newswire: https://www.prnewswire.com/rss/financial-services-latest-news.rss
  - Business Wire: https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeEFpRXQ==
  - GlobeNewsWire: https://www.globenewswire.com/RssFeed/orgclass/1/feedTitle/GlobeNewswire
수집방식  : RSS (feedparser)
핵심 데이터:
  - 기업 공식 보도자료 (실적 발표, 계약 체결, 인수합병 등)
차별점    : 기업이 직접 발표한 1차 소스 → 높은 신뢰도
구현 파일  : src/collectors/press_release.py (RSS 수집기 확장)
```

### 8.5 소스 신뢰도 가중치 (확장안)

```
현재 소스                          추가 소스
─────────────────────────────     ─────────────────────────────
DART 공시           : 25점        KRX KIND            : 25점
Yahoo Finance       : 18점        SEC EDGAR           : 25점
RSS (한경/매경)     : 18점        PR Newswire 등      : 22점
Naver 금융뉴스      : 15점        네이버 리서치 리포트 : 20점
Google News         : 14점        Finviz              : 16점
Reddit              : 8점         MarketWatch RSS     : 16점
Twitter/X           : 8점         Seeking Alpha       : 14점
Naver 종목토론방    : 6점         StockTwits           : 8점
                                  38커뮤니케이션       : 10점
                                  텔레그램 채널        : 6점
```

### 8.6 추가 구현 우선순위 로드맵

#### Phase 4A - 공시·리서치 강화 (우선)
| 순서 | 소스 | 사유 |
|------|------|------|
| 1 | SEC EDGAR (U1) | 미국 공시 = 주가 영향 최대, 무료 API 제공 |
| 2 | KRX KIND (K1) | 거래소 직접 공시, DART 보완 |
| 3 | 네이버 리서치 (K3) | 증권사 투자의견·목표가 = 개인 투자자 영향 大 |
| 4 | PR Newswire/BW (U4) | 기업 공식 보도자료, RSS로 간편 수집 |

#### Phase 4B - 뉴스 소스 다양화
| 순서 | 소스 | 사유 |
|------|------|------|
| 5 | Finviz (U2) | 미국 종목별 뉴스 통합 허브 |
| 6 | 이데일리/머니투데이 (K4/K5) | 국내 뉴스 커버리지 확대 |
| 7 | MarketWatch/CNBC (U6/U7) | 미국 시장 뉴스 보강 |
| 8 | StockTwits (U3) | 미국 개인투자자 심리 데이터 |

#### Phase 4C - 대체 데이터
| 순서 | 소스 | 사유 |
|------|------|------|
| 9 | 38커뮤니케이션 (K2) | IPO 특화 정보 |
| 10 | Seeking Alpha (U5) | 심층 분석 |
| 11 | 텔레그램 (K8) | 속보성 데이터 |
| 12 | YouTube 자막 (C3) | 대체 데이터 실험 |

### 8.7 추가 소스 공통 구현 가이드

```
1. 모든 수집기는 BaseCollector를 상속하여 구현
2. collect() 메서드에서 List[NewsItem]을 반환
3. config.yaml에 enabled/disabled 플래그 추가
4. 소스별 rate limit 준수 (sleep 간격 설정)
5. 실패 시 로그 기록 후 다음 소스 계속 진행 (기존 에러 처리 패턴 유지)
6. 소스 신뢰도 점수를 SOURCE_CREDIBILITY 딕셔너리에 등록
```

---

## 9. 주요 라이브러리

| 라이브러리 | 용도 | 버전 |
|-----------|------|------|
| requests | HTTP 요청 | >=2.31 |
| beautifulsoup4 | HTML 파싱 | >=4.12 |
| feedparser | RSS 파싱 | >=6.0 |
| yfinance | 미국 주가/뉴스 | >=0.2.36 |
| pykrx | 국내 주가 | >=1.0.45 |
| langchain | LLM 체인 | >=0.3 |
| langchain-openai | OpenAI 호환 LLM | >=0.3 |
| rich | CLI 테이블 출력 | >=13.0 |
| pandas | CSV 처리 | >=2.1 |
| streamlit | 웹 대시보드 | >=1.30 |
| fastapi | REST API 서버 | >=0.115 |
| uvicorn | ASGI 서버 | >=0.34 |
| apscheduler | 스케줄러 | >=3.10 |
| pyyaml | YAML 설정 | >=6.0 |
