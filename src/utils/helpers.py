# src/utils/helpers.py
# ============================================================
# 파일명  : helpers.py
# 버전    : V0p1
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p1  최초 작성 — 공통 유틸리티 함수
# ============================================================

from datetime import date, datetime, timezone
from typing import Optional


def today_kst() -> date:
    """한국 표준시(KST, UTC+9) 기준 오늘 날짜를 반환한다.

    Returns:
        date: KST 기준 오늘 날짜
    """
    from datetime import timedelta

    return (datetime.now(tz=timezone.utc) + timedelta(hours=9)).date()


def format_price_change(change: Optional[float]) -> str:
    """가격 변동률을 화살표 포함 문자열로 포맷한다.

    Args:
        change: 변동률 (예: 2.5, -1.3). None이면 '-' 반환

    Returns:
        str: 포맷된 문자열 (예: '▲ 2.50%', '▼ 1.30%')
    """
    if change is None:
        return "-"
    arrow = "▲" if change >= 0 else "▼"
    return f"{arrow} {abs(change):.2f}%"


def format_large_number(value: Optional[float], prefix: str = "$") -> str:
    """큰 숫자를 K/M/B 단위로 포맷한다.

    Args:
        value: 포맷할 숫자. None이면 '-' 반환
        prefix: 접두사 (기본값: '$')

    Returns:
        str: 포맷된 문자열 (예: '$1.23T', '$456.78B')
    """
    if value is None:
        return "-"

    if value >= 1_000_000_000_000:
        return f"{prefix}{value / 1_000_000_000_000:.2f}T"
    elif value >= 1_000_000_000:
        return f"{prefix}{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{prefix}{value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{prefix}{value / 1_000:.2f}K"
    return f"{prefix}{value:.2f}"


def sentiment_to_emoji(sentiment: Optional[str]) -> str:
    """센티멘트 문자열을 이모지로 변환한다.

    Args:
        sentiment: 'positive', 'negative', 'neutral' 중 하나

    Returns:
        str: 대응 이모지 문자열
    """
    mapping = {
        "positive": "🟢 긍정",
        "negative": "🔴 부정",
        "neutral": "🟡 중립",
    }
    return mapping.get(sentiment or "", "⚪ 알 수 없음")


def truncate_text(text: str, max_len: int = 150) -> str:
    """텍스트를 지정된 길이로 자르고 '...'을 붙인다.

    Args:
        text: 원본 텍스트
        max_len: 최대 문자 수

    Returns:
        str: 잘린 텍스트
    """
    if not text:
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text


def parse_date_param(date_str: Optional[str]) -> date:
    """날짜 문자열을 date 객체로 변환한다. 빈 값이면 오늘(KST) 반환.

    Args:
        date_str: 'YYYY-MM-DD' 형식 날짜 문자열 또는 None

    Returns:
        date: 파싱된 날짜 (오류 시 오늘 KST 날짜)
    """
    if not date_str:
        return today_kst()
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return today_kst()
