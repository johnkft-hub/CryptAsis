# src/db/queries.py
# ============================================================
# 파일명  : queries.py
# 버전    : V0p2
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p1  최초 작성 — 뉴스/가격/분석 CRUD 쿼리
# 2026-05-13  V0p2  뉴스 통계용 쿼리 추가 (일별/누적/소스/코인)
# ============================================================

from datetime import date, datetime
from typing import Optional
from supabase import Client


# ── 뉴스 ────────────────────────────────────────────────────

def insert_news(client: Client, news_list: list[dict]) -> int:
    """뉴스 목록을 crypto_news 테이블에 저장한다.

    중복 URL은 DB 유니크 제약(url 컬럼)으로 자동 무시된다.

    Args:
        client: Supabase 클라이언트
        news_list: 저장할 뉴스 딕셔너리 목록

    Returns:
        int: 저장 성공 건수
    """
    if not news_list:
        return 0

    result = (
        client.table("crypto_news")
        .upsert(news_list, on_conflict="url", ignore_duplicates=True)
        .execute()
    )
    return len(result.data) if result.data else 0


def get_news_by_date(
    client: Client,
    target_date: date,
    coins: Optional[list[str]] = None,
    limit: int = 50,
) -> list[dict]:
    """특정 날짜의 뉴스를 조회한다.

    Args:
        client: Supabase 클라이언트
        target_date: 조회할 날짜
        coins: 필터링할 코인 목록 (예: ['BTC', 'ETH']). None이면 전체 조회
        limit: 최대 조회 건수

    Returns:
        list[dict]: 뉴스 딕셔너리 목록
    """
    date_str = target_date.isoformat()
    next_day = target_date.replace(day=target_date.day + 1).isoformat()

    query = (
        client.table("crypto_news")
        .select("*")
        .gte("published_at", date_str)
        .lt("published_at", next_day)
        .order("published_at", desc=True)
        .limit(limit)
    )

    if coins:
        query = query.overlaps("coins", coins)

    result = query.execute()
    return result.data or []


def get_latest_news(client: Client, limit: int = 20) -> list[dict]:
    """최신 뉴스를 조회한다.

    Args:
        client: Supabase 클라이언트
        limit: 최대 조회 건수

    Returns:
        list[dict]: 뉴스 딕셔너리 목록
    """
    result = (
        client.table("crypto_news")
        .select("*")
        .order("published_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


# ── 가격 ────────────────────────────────────────────────────

def insert_prices(client: Client, price_list: list[dict]) -> int:
    """가격 데이터를 crypto_prices 테이블에 저장한다.

    Args:
        client: Supabase 클라이언트
        price_list: 저장할 가격 딕셔너리 목록

    Returns:
        int: 저장 건수
    """
    if not price_list:
        return 0

    result = client.table("crypto_prices").insert(price_list).execute()
    return len(result.data) if result.data else 0


def get_prices_by_coin(
    client: Client,
    coin: str,
    days: int = 7,
) -> list[dict]:
    """특정 코인의 최근 가격 이력을 조회한다.

    Args:
        client: Supabase 클라이언트
        coin: 코인 심볼 (예: 'BTC', 'ETH')
        days: 조회할 일수

    Returns:
        list[dict]: 가격 딕셔너리 목록 (최신순)
    """
    from datetime import timedelta

    since = (datetime.utcnow() - timedelta(days=days)).isoformat()

    result = (
        client.table("crypto_prices")
        .select("*")
        .eq("coin", coin)
        .gte("fetched_at", since)
        .order("fetched_at", desc=True)
        .execute()
    )
    return result.data or []


# ── AI 분석 ─────────────────────────────────────────────────

def insert_analysis(client: Client, analysis: dict) -> bool:
    """AI 분석 결과를 crypto_analysis 테이블에 저장한다.

    Args:
        client: Supabase 클라이언트
        analysis: 저장할 분석 딕셔너리

    Returns:
        bool: 저장 성공 여부
    """
    result = client.table("crypto_analysis").insert(analysis).execute()
    return bool(result.data)


def get_analysis_by_date(
    client: Client,
    target_date: date,
    coin: Optional[str] = None,
) -> list[dict]:
    """특정 날짜의 AI 분석 결과를 조회한다.

    Args:
        client: Supabase 클라이언트
        target_date: 조회할 날짜
        coin: 필터링할 코인 심볼. None이면 전체 조회

    Returns:
        list[dict]: 분석 딕셔너리 목록
    """
    query = (
        client.table("crypto_analysis")
        .select("*")
        .eq("analysis_date", target_date.isoformat())
        .order("created_at", desc=True)
    )

    if coin:
        query = query.eq("coin", coin)

    result = query.execute()
    return result.data or []


# ── 뉴스 통계 ────────────────────────────────────────────────

def get_news_for_stats(
    client: Client,
    days: int = 30,
) -> list[dict]:
    """통계 분석용 뉴스 데이터를 조회한다.

    published_at, source, coins 컬럼만 가져와 데이터 전송량을 최소화한다.

    Args:
        client: Supabase 클라이언트
        days: 최근 몇 일치 데이터를 조회할지

    Returns:
        list[dict]: {'published_at', 'source', 'coins', 'created_at'} 목록
    """
    from datetime import timedelta

    since = (datetime.utcnow() - timedelta(days=days)).isoformat()

    result = (
        client.table("crypto_news")
        .select("published_at, source, coins, created_at")
        .gte("created_at", since)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


def get_news_total_count(client: Client) -> int:
    """DB에 저장된 전체 뉴스 건수를 반환한다.

    Args:
        client: Supabase 클라이언트

    Returns:
        int: 전체 뉴스 건수
    """
    result = (
        client.table("crypto_news")
        .select("id", count="exact")
        .execute()
    )
    return result.count or 0
