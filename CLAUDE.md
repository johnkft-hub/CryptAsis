# CLAUDE.md — Claude Code 모델 지침
# ============================================================
# 파일명  : CLAUDE.md
# 버전    : V0p1
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p0  최초 작성 (ClaudeV0p4.md 기반)
# 2026-05-13  V0p1  CryptAsis 프로젝트 컨텍스트 추가
# ============================================================

## Model Assignment Rules

- 아키텍처 설계, DB 스키마 결정: claude-opus-4-5
- 기능 구현, 리팩토링, 버그 수정: claude-sonnet-4-5
- 파일 검색, 주석 추가, 단순 편집: claude-haiku-4-5

### 작업 유형별 예시

| 작업 | 모델 |
|------|------|
| DB 스키마 설계, 전체 아키텍처 결정, 보안 리뷰 | claude-opus-4-5 |
| API 연동 코드, Streamlit UI, Supabase 쿼리 구현 | claude-sonnet-4-5 |
| 테스트 코드 작성, 리팩토링, 버그 수정 | claude-sonnet-4-5 |
| 주석 추가, 파일명 변경, 단순 텍스트 검색 | claude-haiku-4-5 |

---

## Project Context

- 프로젝트명: CryptAsis — 크립토 뉴스 & 가격 상관관계 분석기
- Stack: Python + Supabase + Streamlit + Groq
- Local path: D:\17_my_project\004_CryptAsis
- DB: Supabase (RLS 필수)
- AI 모델: llama-3.3-70b-versatile (Groq)
- 저장소: github.com/johnkft-hub
- 뉴스 소스: CryptoCompare News API (무료)
- 가격 소스: CoinGecko API (무료)
- 분석 대상: Bitcoin (BTC), Ethereum (ETH)

---

## Code Conventions

- 환경변수는 반드시 .env에서 로드 (python-dotenv)
- 코드 내 API Key, DB URL 하드코딩 절대 금지
- 함수 단위 테스트 작성 (tests/ 폴더)
- 함수마다 docstring 작성
- Conventional Commits 형식으로 커밋
  - feat: 뉴스 수집 함수 추가
  - fix: CoinGecko API 파싱 오류 수정
  - docs: README 설치 방법 업데이트
  - refactor: utils 함수 모듈 분리
  - test: test_api.py 테스트 케이스 추가
  - chore: requirements.txt 패키지 업데이트

---

## Project Structure

```
004_CryptAsis/
├── .env                    # [보안] gitignore 필수
├── .env.example            # [공개] 키 이름만, 값 비워둠
├── .gitignore
├── CLAUDE.md               # 본 파일
├── README.md
├── requirements.txt
├── src/
│   ├── app.py              # Streamlit 메인 앱
│   ├── db/
│   │   ├── client.py       # Supabase 클라이언트
│   │   └── queries.py      # RLS 적용 쿼리
│   ├── api/
│   │   ├── groq_client.py  # Groq API 호출
│   │   ├── news_client.py  # CryptoCompare 뉴스 수집
│   │   ├── price_client.py # CoinGecko 가격 수집
│   │   └── prompts.py      # 프롬프트 템플릿
│   └── utils/
│       └── helpers.py
├── tests/
│   ├── test_db.py
│   └── test_api.py
└── docs/
    ├── reports/
    └── guidebook/
```
