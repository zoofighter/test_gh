# Plan: 뉴스 중요도 라벨링 + ML 랭킹 시스템 구현

> 작성일: 2026-03-08
> 상태: 설계 (미구현)

---

## Context

사용자의 핵심 의도: **주가 없이 순수하게 뉴스 텍스트만으로 중요도를 판단하는 시스템**을 만들고 싶다.

현재 시스템은 뉴스 메타데이터(소스, 보도량, 키워드 유무)에 의존하며 본문 내용을 거의 분석하지 않는다.
사용자가 직접 뉴스에 5단계 등급을 부여하고, 그 데이터로 ML 모델을 학습시켜 자동 랭킹을 생성하는 구조를 구현한다.

**사용자 결정 사항:**
- 라벨링 방식: 5단계 등급 (매우중요=5 / 중요=4 / 보통=3 / 낮음=2 / 무관=1)
- 라벨링 속도: 50건/일 (4일이면 200건, 10일이면 500건)
- 에이전트 역할: LLM이 뉴스를 읽고 중요도 판단 → 사람 라벨과 비교 검증
- BERT 불필요: TF-IDF + 키워드/문맥 기반의 가벼운 모델
- 주가 검증은 나중에: 모델이 안정된 후 주가/거래량으로 최종 확인

---

## 전체 흐름

```
[1단계] 사람이 뉴스 읽고 → 직접 5단계 등급 부여 (라벨링)
           ↓
[2단계] TF-IDF + 키워드/문맥 기반 → ML 모델 학습 (BERT 없이)
           ↓
[3단계] 새 뉴스 → 모델이 자동 등급 예측
           ↓
[4단계] 검증: 사람 검증 + LLM 검증 → 이후 주가/거래량으로 최종 확인
```

---

## 구현 범위

### Step 1: DB 스키마 확장
- `news_labels` 테이블 추가 (사람 라벨 + LLM 라벨 저장)

### Step 2: CLI 라벨링 도구
- `labeler.py` — 터미널에서 뉴스를 보고 5단계 등급 부여
- DB의 최근 뉴스를 하나씩 보여주고 점수 입력

### Step 3: LLM 자동 라벨링
- `llm_labeler.py` — LM Studio가 뉴스를 읽고 5단계 등급 자동 부여
- 사람 라벨과 비교하여 일치율 출력

### Step 4: ML 모델 학습
- `src/ml/features.py` — 텍스트 특징 추출 (TF-IDF + 수작업 특징)
- `src/ml/model.py` — LightGBM 학습/예측/저장
- BERT 없이 TF-IDF + 키워드/문맥 기반

### Step 5: 기존 파이프라인 통합
- `NewsRankingEngine`에 ML content_score 추가 (5번째 스코어)
- 학습 데이터 부족 시 기존 규칙 기반 유지

---

## 수정/생성 파일 목록

| 파일 | 작업 | 설명 |
|------|------|------|
| `src/database/models.py` | 수정 | `news_labels` 테이블 추가 |
| `src/database/repository.py` | 수정 | 라벨 CRUD 메서드 추가 |
| `labeler.py` | 생성 | CLI 사람 라벨링 도구 |
| `llm_labeler.py` | 생성 | LLM 자동 라벨링 + 검증 |
| `src/ml/__init__.py` | 생성 | 패키지 초기화 |
| `src/ml/features.py` | 생성 | TF-IDF + 수작업 특징 추출 |
| `src/ml/model.py` | 생성 | NewsImportanceModel (LightGBM) |
| `src/ranking/engine.py` | 수정 | content_score 통합 |
| `requirements.txt` | 수정 | lightgbm, scikit-learn 추가 |

---

## 상세 설계

### 1. DB 스키마 (`src/database/models.py`)

```sql
CREATE TABLE IF NOT EXISTS news_labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_id INTEGER NOT NULL,
    label INTEGER NOT NULL,          -- 1~5 (무관~매우중요)
    labeler TEXT NOT NULL,           -- 'human' 또는 'llm'
    reason TEXT,                     -- 판단 근거
    labeled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (news_id) REFERENCES news(id)
);
CREATE INDEX IF NOT EXISTS idx_labels_news_id ON news_labels(news_id);
CREATE INDEX IF NOT EXISTS idx_labels_labeler ON news_labels(labeler);
```

### 2. CLI 라벨링 도구 (`labeler.py`)

```
$ python labeler.py              # 라벨링 안 된 뉴스부터 시작
$ python labeler.py --stats      # 라벨링 현황 조회
$ python labeler.py --export     # CSV 내보내기

[1/50] ────────────────────────────────────
출처: dart | 카테고리: 공시
제목: 삼성전자, 10조원 규모 미국 반도체 공장 신설 결정
내용: 삼성전자는 이사회를 열고...
──────────────────────────────────────────
등급 (5=매우중요 4=중요 3=보통 2=낮음 1=무관, s=건너뛰기, q=종료): 5
사유 (선택, Enter=생략): 대규모 투자 확정 공시
✓ 저장 완료 [5점]
```

- 기존 `repo.get_recent_news()`로 뉴스 조회
- 이미 라벨링된 뉴스는 건너뜀
- 50건 단위로 진행 현황 표시

### 3. LLM 자동 라벨링 (`llm_labeler.py`)

```
$ python llm_labeler.py              # 라벨링 안 된 뉴스에 LLM 라벨 부여
$ python llm_labeler.py --compare    # 사람 라벨 vs LLM 라벨 비교

[LLM 라벨링] 50건 처리 중...
  - 완료: 48건, 실패: 2건

[비교 결과] (사람 라벨 존재하는 건)
  - 일치율: 72% (완전 일치)
  - ±1 이내: 91%
  - 평균 차이: 0.4등급
```

- 기존 `lm_studio` 설정 재사용 (config.yaml)
- 프롬프트: 뉴스 제목+본문 → 1~5 등급 + 사유 JSON 응답
- 결과를 `news_labels` 테이블에 `labeler='llm'`으로 저장

### 4. ML 모델 (`src/ml/`)

**features.py** — 특징 추출:
- TF-IDF (max_features=3000) on title+content
- 수작업 특징 ~15개: 수치 존재, 확정도 키워드, 정보 밀도, 소스, 카테고리 등
- 기존 `HIGH_IMPACT_KEYWORDS` (`engine.py:76-87`) 재사용

**model.py** — NewsImportanceModel:
- `train()`: news_labels에서 human 라벨 가져와 LightGBM 학습
- `predict(title, content)`: 1~5 점수 예측
- `evaluate()`: 교차 검증 R², MAE 출력
- `save()/load()`: joblib으로 models/ 디렉토리에 저장

### 5. 랭킹 통합 (`src/ranking/engine.py`)

기존 4항목(각 25점) → 5항목(각 20점)으로 변경:

```
Coverage(20) + Keyword(20) + Source(20) + Relevance(20) + Content(20) = 100
                                                          ↑ ML 예측
```

학습 데이터 양에 따라 점진적 전환:
- 0~50건: 규칙 기반 100%
- 50~200건: ML 비중 점진 증가
- 200건+: ML 비중 안정화

---

## 학습 데이터 축적 로드맵

| 축적량 | 소요 기간 (50건/일) | 모델 수준 |
|--------|-------------------|----------|
| 100건 | 2일 | 학습 가능하나 불안정 |
| **200건** | **4일** | **최소 학습 가능선** |
| 500건 | 10일 | 안정적 |
| 1000건+ | 20일 | 높은 정확도 |

---

## 모델이 학습하는 것

사람이 200건을 평가하면, 모델은 이런 패턴을 스스로 발견:

```
사람이 5점 준 뉴스들의 공통점:
  → "결정", "확정", "승인" 같은 단어가 자주 등장
  → "10조", "50%" 같은 큰 숫자 포함
  → 특정 기업명이 명시됨

사람이 1점 준 뉴스들의 공통점:
  → "시황", "요약", "전망" 같은 단어가 많음
  → 구체적 숫자가 없음
  → 특정 기업이 아닌 업종 전반 이야기
```

사람이 명시적으로 규칙을 알려주지 않아도, 평가 데이터의 패턴에서 모델이 자동으로 학습.

---

## BERT 없이 되는 이유

| 방식 | 정확도 | 속도 | 필요 데이터 |
|------|--------|------|-----------|
| **TF-IDF + LightGBM** | 충분 | 1초 이내 | 200건+ |
| BERT | 약간 더 높음 | 수십 초 | 1000건+ |

뉴스 중요도는 대부분 **키워드 존재 여부 + 수치 크기 + 표현 확정도**로 판단됨.
이것은 TF-IDF가 잘 잡아내는 영역. BERT가 필요한 "미묘한 문맥 이해"는 이 태스크에서 비중이 작음.

---

## 검증 방법

### A. 교차 검증 (자동)

200건 중 160건으로 학습 → 40건으로 테스트:

```
R² = 0.45  →  "사람 판단의 45%를 설명" (괜찮음)
MAE = 0.7  →  "평균 0.7등급 차이" (5점 만점 기준 양호)
```

### B. 사람 vs LLM vs 모델 비교

```
뉴스: "SK하이닉스, HBM 대규모 수주 계약 체결"

사람 평가:  5 (매우중요)
LLM 평가:  5 (매우중요)  ← 일치
ML 모델:   4.3 → 반올림 4 (중요)  ← ±1 이내
```

### C. 주가 사후 검증 (나중에)

모델이 안정된 후:
```
모델이 5점 준 뉴스들 → 발행 후 주가 평균 변동: ±3.2%
모델이 1점 준 뉴스들 → 발행 후 주가 평균 변동: ±0.4%
→ 차이가 크면 모델이 잘 작동하는 것
```

---

## 실행 명령어

```bash
# 1. 의존성 설치
pip install lightgbm scikit-learn joblib

# 2. 뉴스 수집 (라벨링할 데이터 확보)
python main.py

# 3. 사람 라벨링 (매일 50건)
python labeler.py

# 4. LLM 라벨링 + 비교
python llm_labeler.py
python llm_labeler.py --compare

# 5. 라벨링 현황 확인
python labeler.py --stats

# 6. 모델 학습 (200건 이상 축적 후)
python -m src.ml.model --train

# 7. 기존 파이프라인에 ML 점수 포함하여 실행
python main.py
```
