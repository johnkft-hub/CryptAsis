# CryptAsis — 크립토 뉴스 & 가격 상관관계 분석기

크립토(Bitcoin, Ethereum) 주요 뉴스를 매일 수집하고, 가격 변화와의 상관관계를
Groq AI(llama-3.3-70b-versatile)가 분석하여 Streamlit 대시보드로 제공합니다.

---

## 주요 기능

- **뉴스 수집**: CryptoCompare News API에서 BTC/ETH 최신 뉴스 자동 수집
- **가격 수집**: CoinGecko API에서 BTC/ETH 실시간 및 히스토리 가격 수집
- **AI 상관관계 분석**: Groq llama-3.3-70b-versatile이 뉴스 센티멘트와 가격 변동 상관관계 분석
- **대시보드**: Streamlit 기반 인터랙티브 차트 및 분석 결과 시각화
- **DB 저장**: Supabase(PostgreSQL + RLS)에 뉴스/가격/분석 결과 저장

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.10+ |
| 웹 UI | Streamlit |
| DB | Supabase (PostgreSQL + RLS) |
| AI 분석 | Groq API (llama-3.3-70b-versatile) |
| 뉴스 API | CryptoCompare News API |
| 가격 API | CoinGecko API |
| 버전 관리 | GitHub (johnkft-hub) |

---

## 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/johnkft-hub/CryptAsis.git
cd CryptAsis
```

### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 열고 실제 API 키 값 입력
```

`.env` 파일에 입력할 항목:

```
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
GROQ_API_KEY=your-groq-api-key
CRYPTOCOMPARE_API_KEY=your-cryptocompare-api-key  # 선택
```

### 5. Supabase 테이블 생성

Supabase 대시보드 SQL Editor에서 아래 쿼리 실행:

```sql
-- 뉴스 테이블
CREATE TABLE crypto_news (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    body TEXT,
    url TEXT,
    source TEXT,
    published_at TIMESTAMPTZ,
    categories TEXT,
    coins TEXT[],
    sentiment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE crypto_news ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_read" ON crypto_news FOR SELECT USING (true);
CREATE POLICY "allow_insert" ON crypto_news FOR INSERT WITH CHECK (true);

-- 가격 테이블
CREATE TABLE crypto_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coin TEXT NOT NULL,
    price_usd NUMERIC,
    change_1h NUMERIC,
    change_24h NUMERIC,
    change_7d NUMERIC,
    market_cap NUMERIC,
    volume_24h NUMERIC,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE crypto_prices ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_read" ON crypto_prices FOR SELECT USING (true);
CREATE POLICY "allow_insert" ON crypto_prices FOR INSERT WITH CHECK (true);

-- AI 분석 결과 테이블
CREATE TABLE crypto_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_date DATE NOT NULL,
    coin TEXT NOT NULL,
    summary TEXT,
    sentiment TEXT,
    price_impact TEXT,
    key_factors TEXT,
    raw_response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE crypto_analysis ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_read" ON crypto_analysis FOR SELECT USING (true);
CREATE POLICY "allow_insert" ON crypto_analysis FOR INSERT WITH CHECK (true);
```

### 6. 앱 실행

```bash
streamlit run src/app.py
```

---

## 프로젝트 구조

```
004_CryptAsis/
├── .env                    # [보안] API 키 (gitignore)
├── .env.example            # [공개] 키 이름만
├── .gitignore
├── CLAUDE.md               # Claude Code 모델 지침
├── README.md
├── requirements.txt
├── src/
│   ├── app.py              # Streamlit 메인 앱
│   ├── db/
│   │   ├── client.py       # Supabase 클라이언트
│   │   └── queries.py      # RLS 적용 쿼리
│   ├── api/
│   │   ├── groq_client.py  # Groq AI 분석
│   │   ├── news_client.py  # CryptoCompare 뉴스
│   │   ├── price_client.py # CoinGecko 가격
│   │   └── prompts.py      # 프롬프트 템플릿
│   └── utils/
│       └── helpers.py      # 공통 유틸리티
├── tests/
│   ├── test_db.py
│   └── test_api.py
└── docs/
    ├── reports/            # 보안검증 + 커밋 레포트
    └── guidebook/          # Guidebook 버전 이력
```

---

## 보안 주의사항

- `.env`, `.streamlit/secrets.toml` 은 절대 GitHub에 올리지 마세요.
- Supabase RLS(Row Level Security)가 반드시 활성화되어 있어야 합니다.
- 코드 내 API 키 하드코딩 금지.
