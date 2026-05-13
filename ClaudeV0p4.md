# CLAUDE.md — Claude Code 모델 지침
# ============================================================
# 파일명  : CLAUDE.md
# 버전    : V0p4
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p1  최초 작성 — 기본 모델 배정 규칙 정의
# 2026-05-13  V0p2  모델명 풀네임으로 변경, Project Context 추가
# 2026-05-13  V0p3  Commits 예시 추가 (들여쓰기 수정), 이력헤드 추가
# 2026-05-13  V0p4  Commits 예시 들여쓰기 정리, 이력헤드 버전 정정
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

- Stack: Python + Supabase + Streamlit + Groq
- Local path: D:\17_my_project
- DB: Supabase (RLS 필수)
- AI 모델: llama-3.3-70b-versatile (Groq)
- 저장소: github.com/johnkft-hub

---

## Code Conventions

- 환경변수는 반드시 .env에서 로드 (python-dotenv)
- 코드 내 API Key, DB URL 하드코딩 절대 금지
- 함수 단위 테스트 작성 (tests/ 폴더)
- 함수마다 docstring 작성
- Conventional Commits 형식으로 커밋
  - feat: Groq API 연동 함수 추가
  - fix: Supabase 연결 오류 수정
  - docs: README 설치 방법 업데이트
  - refactor: utils 함수 모듈 분리
  - test: test_api.py 테스트 케이스 추가
  - chore: requirements.txt 패키지 업데이트

---

## Project Structure

```
my_project/
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
│   │   └── prompts.py      # 프롬프트 템플릿
│   └── utils/
│       └── helpers.py
├── tests/
│   ├── test_db.py
│   └── test_api.py
├── docs/
│   ├── reports/            # 보안검증 + 커밋 레포트
│   └── guidebook/          # Guidebook 버전 이력
└── .streamlit/
    └── secrets.toml        # [보안] gitignore 필수
```
