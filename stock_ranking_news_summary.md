# 주식 랭킹 뉴스 시스템 프로젝트 요약 (Summary)

> 작성일: 2026-03-05

이 문서는 `stock_ranking_news_spec.md` 에 정의된 요건을 바탕으로 주식 랭킹 뉴스 시스템의 전체 작업 내용 및 아키텍처를 요약한 문서입니다.

## 1. 프로젝트 개요
주식 시장(한국 KOSPI/KOSDAQ, 미국 NYSE/NASDAQ)의 다양한 뉴스 소스를 수집하고, **로컬 LLM(LangChain + LM Studio)** 을 활용하여 개별 주가에 큰 영향을 미칠 수 있는 '랭킹 뉴스'를 선별 및 제공하는 파이썬 기반 자동화 시스템입니다.

## 2. 주요 아키텍처 및 워크플로우
시스템은 크게 5단계의 데이터 파이프라인으로 구성됩니다.
1. **뉴스 수집 (Collectors):** 네이버 금융, DART 공시, Yahoo Finance, 주요 미디어 RSS 등에서 정보 수집 (Phase 2에서 SNS, 종목토론방 추가)
2. **전처리 (Preprocessor):** 수집된 뉴스의 중복을 제거하고, 관련된 주식 종목을 매핑하며 카테고리(실적, M&A 등)를 분류
3. **주가 데이터 결합 (Stock Data):** pykrx(국내) 및 yfinance(미국)를 활용해 해당 종목의 일봉 종가 및 거래량 급증 데이터 스크랩
4. **랭킹 엔진 (Ranking Engine):** LangChain 체인과 로컬 LLM을 통해 4가지 지표(중복성, 키워드 중요도, 주가 변동성, 소스 신뢰도)를 기준으로 순위를 산정 (LLM 오류 시 자체 폴백 로직 적용)
5. **저장 및 출력 (DB & Output):** SQLite 데이터베이스에 이력을 저장하고 터미널 CLI, CSV, 및 Streamlit 웹 대시보드, 텔레그램 등으로 결과 요약 출력

## 3. 핵심 기술 스택
- **언어:** Python 3.10+
- **AI/분석:** LangChain, langchain-openai, LM Studio (로컬)
- **데이터베이스:** SQLite (추후 PostgreSQL 확장 가능)
- **데이터 소스 처리:** BeautifulSoup4, Feedparser, yfinance, pykrx 등
- **인터페이스 & 자동화:** Streamlit(대시보드), FastAPI(REST API), APScheduler(장전/장후 정기 실행)

## 4. 진행 단계 (Milestones)
- **Phase 1 (MVP 구현):** 기초적인 수집/전처리 로직 구축, LLM 기반 랭킹 도입 및 DB 저장, 기본 CLI 출력
- **Phase 2 (소스 확장 & UI 구성):** 추가 소스(트위터, 토론방 등) 크롤링, Streamlit 대시보드 도입, 텔레그램 알림, 패턴(거래량 급증) 감지 추가
- **Phase 3 (자동화 & API 제공):** 스케줄러 자동화, 가중치 최적화, FastAPI를 통한 REST API 서비스화
- **Phase 4 (추가 소스 통합, 확장 로드맵):** 한국증권거래소(KIND), 증권사 리포트, 미국 SEC EDGAR, Finviz 등 공신력 높은 보충 정보 소스 통합

## 5. 기대 효과 및 활용방안
- 개인 투자자가 수많은 정보 속에서 주가 변동성에 유의미한 뉴스를 빠르게 파악할 수 있도록 도울 수 있음.
- 로컬 환경의 LLM을 사용하여 개인정보 민감도나 API 비용 부담 없이 시스템의 고도화 및 커스터마이징 가능.
- 추후 퀀트 투자나 자동 매매 봇과 연계하기 쉬운 REST API 구조 제공.
