# src/utils/config.py
# ============================================================
# 파일명  : config.py
# 버전    : V0p1
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p1  최초 작성 — 로컬(.env) / 클라우드(st.secrets) 통합 설정
# ============================================================

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def get_secret(key: str, default: str = "") -> str:
    """환경변수 또는 Streamlit secrets에서 설정값을 가져온다.

    Streamlit Cloud 배포 시에는 st.secrets를 우선 사용하고,
    로컬 개발 시에는 .env 파일의 환경변수를 사용한다.

    매개변수:
        key: 설정 키 이름
        default: 기본값 (키가 없을 때 반환)

    반환값:
        str: 설정값
    """
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass

    return os.getenv(key, default)


def get_supabase_config() -> tuple[str, str]:
    """Supabase URL과 ANON KEY를 반환한다.

    반환값:
        tuple[str, str]: (SUPABASE_URL, SUPABASE_ANON_KEY)

    예외:
        RuntimeError: 설정값 미존재 시
    """
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL 또는 SUPABASE_ANON_KEY가 설정되지 않았습니다."
        )
    return url, key


def get_groq_api_key() -> str:
    """Groq API 키를 반환한다.

    반환값:
        str: GROQ_API_KEY

    예외:
        RuntimeError: 키 미설정 시
    """
    key = get_secret("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY가 설정되지 않았습니다.")
    return key


def get_naver_config() -> tuple[str, str]:
    """네이버 API Client ID와 Secret을 반환한다.

    반환값:
        tuple[str, str]: (NAVER_CLIENT_ID, NAVER_CLIENT_SECRET)
    """
    return (
        get_secret("NAVER_CLIENT_ID"),
        get_secret("NAVER_CLIENT_SECRET"),
    )
