# src/api/news_client.py
# ============================================================
# 파일명  : news_client.py
# 버전    : V0p1
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p1  최초 작성 — CryptoCompare News API 연동
# ============================================================

import os
from datetime import datetime, timezone
from typing import Optional

import requests
from dotenv import load_dotenv

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

_SSL_VERIFY = True

load_dotenv()

_BASE_URL = "https://min-api.cryptocompare.com/data/v2/news/"
_CATEGORIES = "BTC,ETH,Blockchain,Trading"


def fetch_crypto_news(
    coins: Optional[list[str]] = None,
    limit: int = 50,
    lang: str = "EN",
) -> list[dict]:
    """CryptoCompare에서 최신 크립토 뉴스를 가져온다.

    API 키가 없어도 무료 플랜으로 동작하나, 키가 있으면 요청 제한이 완화된다.

    Args:
        coins: 필터링할 코인 심볼 목록 (예: ['BTC', 'ETH']). None이면 전체
        limit: 가져올 최대 뉴스 수 (최대 50)
        lang: 언어 코드 ('EN' 권장)

    Returns:
        list[dict]: 정규화된 뉴스 딕셔너리 목록

    Raises:
        requests.HTTPError: API 오류 시
    """
    api_key = os.getenv("CRYPTOCOMPARE_API_KEY", "")
    headers = {"authorization": f"Apikey {api_key}"} if api_key else {}

    categories = ",".join(coins) if coins else _CATEGORIES
    params = {
        "categories": categories,
        "excludeCategories": "Sponsored",
        "lTs": 0,
        "lang": lang,
    }

    response = requests.get(_BASE_URL, params=params, headers=headers, timeout=10, verify=_SSL_VERIFY)
    response.raise_for_status()

    data = response.json()
    # API 응답 구조: {"Data": [...]} 또는 {"Data": {"Data": [...]}}
    raw = data.get("Data") or []
    if isinstance(raw, dict):
        raw = raw.get("Data") or []
    raw_items = raw[:limit]
    return [_normalize_news(item) for item in raw_items]


def _normalize_news(item: dict) -> dict:
    """API 응답 뉴스 항목을 DB 저장 형식으로 변환한다.

    Args:
        item: CryptoCompare 원시 뉴스 딕셔너리

    Returns:
        dict: 정규화된 뉴스 딕셔너리
    """
    published_ts = item.get("published_on", 0)
    published_at = (
        datetime.fromtimestamp(published_ts, tz=timezone.utc).isoformat()
        if published_ts
        else None
    )

    categories_raw = item.get("categories", "")
    coins = _extract_coins(categories_raw + " " + item.get("tags", ""))

    return {
        "title": item.get("title", ""),
        "body": item.get("body", ""),
        "url": item.get("url", ""),
        "source": item.get("source_info", {}).get("name", item.get("source", "")),
        "published_at": published_at,
        "categories": categories_raw,
        "coins": coins,
        "sentiment": None,
    }


def _extract_coins(text: str) -> list[str]:
    """텍스트에서 언급된 코인 심볼을 추출한다.

    Args:
        text: 카테고리/태그 문자열

    Returns:
        list[str]: 코인 심볼 목록 (예: ['BTC', 'ETH'])
    """
    known_coins = {"BTC", "ETH", "XRP", "BNB", "SOL", "ADA", "DOGE", "MATIC"}
    text_upper = text.upper()
    return [coin for coin in known_coins if coin in text_upper]
