# 주식 랭킹 뉴스 시스템 - 노드 기반 워크플로우

> 작성일: 2026-03-07

---

## 1. 전체 파이프라인 워크플로우

```mermaid
flowchart TD
    START([python main.py]) --> INIT[설정 로드 + DB 초기화]
    INIT --> STATS_CHECK{--stats?}

    STATS_CHECK -->|Yes| DB_STATS[/DB 현황 출력/]
    DB_STATS --> END_STATS([종료])

    STATS_CHECK -->|No| COLLECT_CHECK{--no-collect?}

    %% ── 수집 단계 ──
    COLLECT_CHECK -->|No| COLLECT[[뉴스 수집]]
    COLLECT --> PREPROCESS[[전처리]]
    PREPROCESS --> PRINT_RESULT[/수집 결과 출력/]
    PRINT_RESULT --> SAVE_CHECK{--no-save?}
    SAVE_CHECK -->|No| SAVE[[DB 저장]]
    SAVE --> SAVE_STATS[/DB 현황 출력/]
    SAVE_STATS --> PRICE_CHECK
    SAVE_CHECK -->|Yes| PRICE_CHECK

    COLLECT_CHECK -->|Yes| PRICE_CHECK{--no-price?}

    %% ── 주가 단계 ──
    PRICE_CHECK -->|No| PRICE[[주가 수집]]
    PRICE --> RANK_CHECK
    PRICE_CHECK -->|Yes| RANK_CHECK{--no-rank?}

    %% ── 랭킹 단계 ──
    RANK_CHECK -->|No| RANKING[[랭킹 분석]]
    RANKING --> PRINT_RANK[/랭킹 결과 출력/]
    PRINT_RANK --> CLEANUP
    RANK_CHECK -->|Yes| CLEANUP

    %% ── 정리 ──
    CLEANUP[30일 초과 데이터 정리] --> END([종료])

    %% 스타일
    style START fill:#4CAF50,color:#fff
    style END fill:#4CAF50,color:#fff
    style END_STATS fill:#4CAF50,color:#fff
    style COLLECT fill:#2196F3,color:#fff
    style PREPROCESS fill:#2196F3,color:#fff
    style SAVE fill:#2196F3,color:#fff
    style PRICE fill:#2196F3,color:#fff
    style RANKING fill:#2196F3,color:#fff
    style CLEANUP fill:#FF9800,color:#fff
```

---

## 2. 뉴스 수집 노드 상세

```mermaid
flowchart TD
    COLLECT_START([collect_news]) --> INIT_LIST[빈 리스트 초기화]

    INIT_LIST --> N1[NaverCollector]
    INIT_LIST --> N2[DartCollector]
    INIT_LIST --> N3[YahooCollector]
    INIT_LIST --> N4[RssCollector]
    INIT_LIST --> N5[GoogleNewsCollector]
    INIT_LIST --> N6[RedditCollector]
    INIT_LIST --> N7[TwitterCollector]
    INIT_LIST --> N8[NaverDiscussionCollector]

    N1 -->|네이버 금융 스크레이핑| R1{성공?}
    N2 -->|DART API 호출| R2{성공?}
    N3 -->|yfinance 호출| R3{성공?}
    N4 -->|RSS feedparser| R4{성공?}
    N5 -->|Google RSS 파싱| R5{성공?}
    N6 -->|Reddit JSON API| R6{성공?}
    N7 -->|Nitter 스크레이핑| R7{성공?}
    N8 -->|네이버 토론방 스크레이핑| R8{성공?}

    R1 -->|Yes| MERGE[all_news.extend]
    R1 -->|No| LOG1[에러 로그]
    R2 -->|Yes| MERGE
    R2 -->|No| LOG2[에러 로그]
    R3 -->|Yes| MERGE
    R3 -->|No| LOG3[에러 로그]
    R4 -->|Yes| MERGE
    R4 -->|No| LOG4[에러 로그]
    R5 -->|Yes| MERGE
    R5 -->|No| LOG5[에러 로그]
    R6 -->|Yes| MERGE
    R6 -->|No| LOG6[에러 로그]
    R7 -->|Yes| MERGE
    R7 -->|No| LOG7[에러 로그]
    R8 -->|Yes| MERGE
    R8 -->|No| LOG8[에러 로그]

    LOG1 --> MERGE
    LOG2 --> MERGE
    LOG3 --> MERGE
    LOG4 --> MERGE
    LOG5 --> MERGE
    LOG6 --> MERGE
    LOG7 --> MERGE
    LOG8 --> MERGE

    MERGE --> OUT([List~NewsItem~ 반환])

    style COLLECT_START fill:#4CAF50,color:#fff
    style OUT fill:#4CAF50,color:#fff
    style N1 fill:#2196F3,color:#fff
    style N2 fill:#2196F3,color:#fff
    style N3 fill:#2196F3,color:#fff
    style N4 fill:#2196F3,color:#fff
    style N5 fill:#2196F3,color:#fff
    style N6 fill:#2196F3,color:#fff
    style N7 fill:#9E9E9E,color:#fff
    style N8 fill:#9E9E9E,color:#fff
```

> N7(Twitter), N8(네이버토론방)은 현재 **비활성** 상태 (회색)

---

## 3. 전처리 파이프라인 노드 상세

```mermaid
flowchart TD
    IN([List~NewsItem~ 입력]) --> DEDUP

    %% ── 중복 제거 ──
    subgraph DEDUP_BOX [1단계: 중복 제거 - dedup.py]
        DEDUP[뉴스 순회 시작] --> COMPARE{seen_titles와\n제목 유사도 비교}
        COMPARE -->|유사도 >= 80%| DUP_YES[중복 판정]
        DUP_YES --> COVERAGE[원본에 coverage_count++\ncoverage_sources 추가]
        COVERAGE --> NEXT_ITEM[다음 뉴스]
        COMPARE -->|유사도 < 80%| DUP_NO[신규 판정]
        DUP_NO --> ADD_UNIQUE[unique 리스트에 추가\ncoverage_count=1 초기화]
        ADD_UNIQUE --> NEXT_ITEM
        NEXT_ITEM --> MORE{남은 뉴스?}
        MORE -->|Yes| COMPARE
        MORE -->|No| DEDUP_OUT[중복 제거 완료]
    end

    %% ── 종목 매핑 ──
    DEDUP_OUT --> MAP

    subgraph MAP_BOX [2단계: 종목 매핑 - stock_mapper.py]
        MAP[뉴스 순회 시작] --> T1{1순위:\n종목명 매칭\nDB + pykrx 사전}
        T1 -->|매칭| SET_CODE[stock_code, stock_name 설정]
        T1 -->|불일치| T2{2순위:\n6자리 숫자 패턴}
        T2 -->|매칭| SET_CODE
        T2 -->|불일치| T3{3순위:\n영문 1~5자 티커}
        T3 -->|매칭| SET_CODE
        T3 -->|불일치| SKIP[매핑 없음]
        SET_CODE --> MAP_NEXT[다음 뉴스]
        SKIP --> MAP_NEXT
        MAP_NEXT --> MAP_MORE{남은 뉴스?}
        MAP_MORE -->|Yes| T1
        MAP_MORE -->|No| MAP_OUT[종목 매핑 완료]
    end

    %% ── 카테고리 분류 ──
    MAP_OUT --> CAT

    subgraph CAT_BOX [3단계: 카테고리 분류 - categorizer.py]
        CAT[뉴스 순회 시작] --> HAS_CAT{이미 카테고리\n있음?}
        HAS_CAT -->|Yes - DART 공시 등| CAT_SKIP[건너뜀]
        HAS_CAT -->|No| KW_MATCH[제목+내용에서\n8개 카테고리 키워드 매칭]
        KW_MATCH --> BEST{최다 매칭\n카테고리?}
        BEST -->|있음| SET_CAT[category 설정]
        BEST -->|없음| NO_CAT[미분류]
        SET_CAT --> CAT_NEXT[다음 뉴스]
        CAT_SKIP --> CAT_NEXT
        NO_CAT --> CAT_NEXT
        CAT_NEXT --> CAT_MORE{남은 뉴스?}
        CAT_MORE -->|Yes| HAS_CAT
        CAT_MORE -->|No| CAT_OUT[카테고리 분류 완료]
    end

    CAT_OUT --> OUT([전처리된 List~NewsItem~ 반환])

    style IN fill:#4CAF50,color:#fff
    style OUT fill:#4CAF50,color:#fff
    style DEDUP_BOX fill:#E3F2FD,stroke:#1565C0
    style MAP_BOX fill:#E8F5E9,stroke:#2E7D32
    style CAT_BOX fill:#FFF3E0,stroke:#E65100
```

---

## 4. DB 저장 노드 상세

```mermaid
flowchart TD
    IN([전처리된 뉴스 입력]) --> REG_START

    subgraph REG [종목 등록 - FK 제약 충족]
        REG_START[뉴스 순회] --> HAS_CODE{stock_code\n있음?}
        HAS_CODE -->|No| REG_NEXT[다음 뉴스]
        HAS_CODE -->|Yes| EXISTS{DB에\n이미 등록?}
        EXISTS -->|Yes| REG_NEXT
        EXISTS -->|No| DETECT{코드 형식?}
        DETECT -->|6자리 숫자| KR[market = KOSPI]
        DETECT -->|영문| US[market = NYSE]
        KR --> UPSERT[upsert_stock]
        US --> UPSERT
        UPSERT --> REG_NEXT
        REG_NEXT --> REG_MORE{남은 뉴스?}
        REG_MORE -->|Yes| HAS_CODE
        REG_MORE -->|No| REG_DONE[종목 등록 완료]
    end

    REG_DONE --> SAVE_START

    subgraph SAVE [뉴스 저장 - URL 중복 체크]
        SAVE_START[뉴스 순회] --> URL_CHECK{URL로\nDB 중복 체크}
        URL_CHECK -->|이미 존재| SKIP_COUNT[skipped++]
        URL_CHECK -->|신규| INSERT[insert_news]
        INSERT --> SAVED_COUNT[saved++]
        SKIP_COUNT --> SAVE_NEXT[다음 뉴스]
        SAVED_COUNT --> SAVE_NEXT
        SAVE_NEXT --> SAVE_MORE{남은 뉴스?}
        SAVE_MORE -->|Yes| URL_CHECK
        SAVE_MORE -->|No| SAVE_DONE[저장 완료 로그]
    end

    SAVE_DONE --> OUT([저장 건수 반환])

    style IN fill:#4CAF50,color:#fff
    style OUT fill:#4CAF50,color:#fff
    style REG fill:#E8F5E9,stroke:#2E7D32
    style SAVE fill:#E3F2FD,stroke:#1565C0
```

---

## 5. 랭킹 분석 노드 상세

```mermaid
flowchart TD
    IN([run_rankings]) --> LOAD[DB에서 최근 24시간 뉴스 로드]
    LOAD --> HAS_NEWS{뉴스\n있음?}
    HAS_NEWS -->|No| EMPTY([빈 결과 반환])

    HAS_NEWS -->|Yes| NEWS_RANK

    subgraph NEWS_RANK_BOX [뉴스 랭킹 - NewsRankingEngine]
        NEWS_RANK[뉴스 배치 분할\n20건씩] --> BATCH[배치 처리]
        BATCH --> LLM_CALL{LM Studio\n호출}
        LLM_CALL -->|성공| PARSE[JSON 응답 파싱\n→ 점수 추출]
        LLM_CALL -->|실패| FALLBACK[규칙 기반 폴백\nscore = news_count*15\n+ price_change*2\n+ volume_change*0.5]
        PARSE --> SCORE[4개 항목 점수 합산]
        FALLBACK --> SCORE

        SCORE --> COV[Coverage Score\nmin 25 count*8]
        SCORE --> KW[Keyword Score\n5단계 티어 매칭]
        SCORE --> SRC[Source Credibility\n소스별 고정 점수]
        SCORE --> MKT[Market Relevance\n종목언급+주가변동+카테고리]

        COV --> TOTAL[총점 0~100]
        KW --> TOTAL
        SRC --> TOTAL
        MKT --> TOTAL

        TOTAL --> SORT[점수 내림차순 정렬]
        SORT --> SAVE_NR[news_rankings 테이블 저장]
    end

    SAVE_NR --> STOCK_CHECK{stock_level\n_enabled?}

    STOCK_CHECK -->|Yes| STOCK_RANK

    subgraph STOCK_RANK_BOX [종목 랭킹 - RankingEngine]
        STOCK_RANK[종목별 뉴스 그룹핑] --> STOCK_BATCH[10종목씩 배치]
        STOCK_BATCH --> STOCK_LLM{LM Studio\n호출}
        STOCK_LLM -->|성공| STOCK_PARSE[JSON 파싱]
        STOCK_LLM -->|실패| STOCK_FALL[규칙 기반 폴백]
        STOCK_PARSE --> STOCK_SCORE[종목 영향력 점수]
        STOCK_FALL --> STOCK_SCORE
        STOCK_SCORE --> STOCK_SORT[점수 정렬]
        STOCK_SORT --> SAVE_SR[rankings 테이블 저장]
    end

    STOCK_CHECK -->|No| IMPACT
    SAVE_SR --> IMPACT

    subgraph IMPACT_BOX [영향력 추적 - ImpactTracker]
        IMPACT[랭킹된 뉴스 조회] --> HAS_IMPACT{이미\n계산됨?}
        HAS_IMPACT -->|Yes| IMP_SKIP[스킵]
        HAS_IMPACT -->|No| BASE[발행일 종가 조회\nbase_price]
        BASE --> D1[1일 후 주가 조회]
        BASE --> D7[7일 후 주가 조회]
        BASE --> D30[30일 후 주가 조회]
        D1 --> CALC[변동률 계산\nchange_pct = \ntarget-base / base * 100]
        D7 --> CALC
        D30 --> CALC
        CALC --> SAVE_IMP[news_impact 테이블 저장]
        IMP_SKIP --> IMP_DONE[추적 완료]
        SAVE_IMP --> IMP_DONE
    end

    IMP_DONE --> OUT([랭킹 결과 반환])

    style IN fill:#4CAF50,color:#fff
    style OUT fill:#4CAF50,color:#fff
    style EMPTY fill:#F44336,color:#fff
    style NEWS_RANK_BOX fill:#E3F2FD,stroke:#1565C0
    style STOCK_RANK_BOX fill:#FFF3E0,stroke:#E65100
    style IMPACT_BOX fill:#F3E5F5,stroke:#7B1FA2
```

---

## 6. 주가 수집 노드 상세

```mermaid
flowchart TD
    IN([fetch_stock_prices]) --> GET_STOCKS[DB에서 전체 종목 조회]
    GET_STOCKS --> HAS{종목\n있음?}
    HAS -->|No| NONE([종목 없음 - 종료])

    HAS -->|Yes| SPLIT[시장별 분류]

    SPLIT --> KR_CHECK{한국 종목\n있음?}
    SPLIT --> US_CHECK{미국 종목\n있음?}

    KR_CHECK -->|Yes| KR

    subgraph KR_BOX [한국 주가 - pykrx]
        KR[pykrx API 호출\n최근 35일] --> KR_LOOP[종목별 순회]
        KR_LOOP --> KR_OHLCV[일봉 OHLCV 조회]
        KR_OHLCV --> KR_CALC[전일대비 변동률 계산]
        KR_CALC --> KR_SAVE[upsert_price]
        KR_SAVE --> KR_ERR{에러?}
        KR_ERR -->|Yes| KR_LOG[에러 로그\n다음 종목 계속]
        KR_ERR -->|No| KR_NEXT[다음 종목]
        KR_LOG --> KR_NEXT
    end

    US_CHECK -->|Yes| US

    subgraph US_BOX [미국 주가 - yfinance]
        US[yfinance API 호출\n최근 35일] --> US_LOOP[종목별 순회]
        US_LOOP --> US_OHLCV[일봉 OHLCV 조회]
        US_OHLCV --> US_CALC[전일대비 변동률 계산]
        US_CALC --> US_SAVE[upsert_price]
        US_SAVE --> US_ERR{에러?}
        US_ERR -->|Yes| US_LOG[에러 로그\n다음 종목 계속]
        US_ERR -->|No| US_NEXT[다음 종목]
        US_LOG --> US_NEXT
    end

    KR_CHECK -->|No| DONE
    US_CHECK -->|No| DONE
    KR_NEXT --> DONE
    US_NEXT --> DONE

    DONE([주가 수집 완료])

    style IN fill:#4CAF50,color:#fff
    style DONE fill:#4CAF50,color:#fff
    style NONE fill:#F44336,color:#fff
    style KR_BOX fill:#FFEBEE,stroke:#C62828
    style US_BOX fill:#E3F2FD,stroke:#1565C0
```

---

## 7. 데이터 흐름 요약도

```mermaid
flowchart LR
    subgraph SOURCES [뉴스 소스]
        S1[네이버]
        S2[DART]
        S3[Yahoo]
        S4[RSS]
        S5[Google]
        S6[Reddit]
    end

    subgraph PREPROCESS [전처리]
        P1[중복 제거]
        P2[종목 매핑]
        P3[카테고리 분류]
    end

    subgraph DATABASE [(SQLite)]
        D1[(stocks)]
        D2[(news)]
        D3[(stock_prices)]
        D4[(news_rankings)]
        D5[(news_impact)]
    end

    subgraph PRICE [주가 소스]
        PR1[pykrx\n한국]
        PR2[yfinance\n미국]
    end

    subgraph RANKING [랭킹]
        R1[LM Studio\nLLM]
        R2[규칙 기반\nFallback]
    end

    subgraph OUTPUT [출력]
        O1[터미널\n랭킹 테이블]
    end

    SOURCES -->|NewsItem| P1
    P1 -->|유니크 뉴스| P2
    P2 -->|종목코드 부여| P3
    P3 -->|카테고리 부여| D2
    P3 --> D1

    PR1 --> D3
    PR2 --> D3

    D2 --> R1
    D3 --> R1
    R1 -->|실패 시| R2
    R1 --> D4
    R2 --> D4

    D4 --> D5
    D3 --> D5

    D4 --> O1

    style SOURCES fill:#E3F2FD,stroke:#1565C0
    style PREPROCESS fill:#E8F5E9,stroke:#2E7D32
    style DATABASE fill:#FFF3E0,stroke:#E65100
    style PRICE fill:#FFEBEE,stroke:#C62828
    style RANKING fill:#F3E5F5,stroke:#7B1FA2
    style OUTPUT fill:#E0F2F1,stroke:#00695C
```
