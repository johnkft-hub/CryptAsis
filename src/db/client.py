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

from supabase import create_client, Client
from src.utils.config import get_supabase_config


def get_supabase_client() -> Client:
    """Supabase 클라이언트를 초기화하여 반환한다.

    로컬: .env의 SUPABASE_URL, SUPABASE_ANON_KEY 사용
    클라우드: Streamlit secrets 사용

    Returns:
        Client: 초기화된 Supabase 클라이언트

    Raises:
        RuntimeError: 설정값 미존재 시
    """
    url, key = get_supabase_config()
    return create_client(url, key)
