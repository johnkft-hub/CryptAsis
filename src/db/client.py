# src/db/client.py
# ============================================================
# 파일명  : client.py
# 버전    : V0p1
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p1  최초 작성 — Supabase 클라이언트 초기화
# ============================================================

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def get_supabase_client() -> Client:
    """Supabase 클라이언트를 초기화하여 반환한다.

    환경변수 SUPABASE_URL, SUPABASE_ANON_KEY를 사용한다.
    값이 없을 경우 RuntimeError를 발생시킨다.

    Returns:
        Client: 초기화된 Supabase 클라이언트

    Raises:
        RuntimeError: 환경변수 미설정 시
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL 또는 SUPABASE_ANON_KEY 환경변수가 설정되지 않았습니다. "
            ".env 파일을 확인하세요."
        )

    return create_client(url, key)
