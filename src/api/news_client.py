# src/api/news_client.py
# ============================================================
# 파일명  : news_client.py
# 버전    : V0p2
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p1  최초 작성 — CryptoCompare News API 연동
# 2026-05-13  V0p2  네이버 뉴스 API + 구글 뉴스 RSS 피드로 교체
# ============================================================

import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import requests
from dotenv import load_dotenv

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

load_dotenv()

_NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"

# 코인별 네이버 검색 키워드
_NAVER_QUERIES = {
    "BTC": "비트코인",
    "ETH": "이더리움",
    "ALL": "비트코인 OR 이더리움 OR 크립토",
}

# 코인별 구글 검색 키워드
_GOOGLE_QUERIES = {
    "BTC": "bitcoin crypto",
    "ETH": "ethereum crypto",
    "ALL": "bitcoin ethereum cryptocurrency",
}


def fetch_crypto_news(
    coins: Optional[list[str]] = None,
    limit: int = 50,
) -> list[dict]:
    """네이버 뉴스(한국)와 구글 뉴스(해외)에서 크립토 뉴스를 통합 수집한다.

    Args:
        coins: 필터링할 코인 심볼 목록 (예: ['BTC', 'ETH']). None이면 전체
        limit: 소스별 최대 수집 건수 (각각 limit//2 건씩)

    Returns:
        list[dict]: 정규화된 뉴스 딕셔너리 목록 (최신순 정렬)
    """
    per_source = max(limit // 2, 10)
    coin_key = coins[0] if coins and len(coins) == 1 else "ALL"

    naver_news = fetch_naver_news(coin_key, limit=per_source)
    google_news = fetch_google_news(coin_key, limit=per_source)

    combined = naver_news + google_news
    combined.sort(key=lambda x: x.get("published_at") or "", reverse=True)
    return combined[:limit]


def fetch_naver_news(coin_key: str = "ALL", limit: int = 20) -> list[dict]:
    """네이버 뉴스 API에서 크립토 뉴스를 수집한다.

    환경변수 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 필요.
    키가 없으면 빈 목록을 반환한다.

    Args:
        coin_key: 코인 키 ('BTC', 'ETH', 'ALL')
        limit: 최대 수집 건수 (최대 100)

    Returns:
        list[dict]: 정규화된 뉴스 딕셔너리 목록
    """
    client_id = os.getenv("NAVER_CLIENT_ID", "")
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        return []

    query = _NAVER_QUERIES.get(coin_key, _NAVER_QUERIES["ALL"])
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {
        "query": query,
        "display": min(limit, 100),
        "start": 1,
        "sort": "date",
    }

    try:
        response = requests.get(
            _NAVER_NEWS_URL,
            headers=headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
        return [_normalize_naver(item, coin_key) for item in items]
    except Exception:
        return []


def fetch_google_news(coin_key: str = "ALL", limit: int = 20) -> list[dict]:
    """구글 뉴스 RSS 피드에서 크립토 뉴스를 수집한다.

    API 키 불필요 — 구글 뉴스 RSS를 직접 파싱한다.

    Args:
        coin_key: 코인 키 ('BTC', 'ETH', 'ALL')
        limit: 최대 수집 건수

    Returns:
        list[dict]: 정규화된 뉴스 딕셔너리 목록
    """
    query = _GOOGLE_QUERIES.get(coin_key, _GOOGLE_QUERIES["ALL"])
    params = {
        "q": query,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    }

    try:
        response = requests.get(
            _GOOGLE_RSS_URL if hasattr(__builtins__, '_GOOGLE_RSS_URL') else _GOOGLE_NEWS_RSS,
            params=params,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()
        return _parse_rss(response.text, coin_key, limit)
    except Exception:
        return []


def _parse_rss(xml_text: str, coin_key: str, limit: int) -> list[dict]:
    """구글 뉴스 RSS XML을 파싱하여 뉴스 목록으로 변환한다.

    Args:
        xml_text: RSS XML 문자열
        coin_key: 코인 키
        limit: 최대 파싱 건수

    Returns:
        list[dict]: 정규화된 뉴스 딕셔너리 목록
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    items = root.findall(".//item")[:limit]
    results = []

    for item in items:
        title = _tag_text(item, "title")
        link = _tag_text(item, "link")
        pub_date = _tag_text(item, "pubDate")
        description = _tag_text(item, "description")
        source_el = item.find("source")
        source = source_el.text if source_el is not None else "Google News"

        published_at = _parse_rfc2822(pub_date)
        coins = _extract_coins(f"{title} {description}")

        results.append({
            "title": title,
            "body": _strip_html(description),
            "url": link,
            "source": source,
            "published_at": published_at,
            "categories": "Google News",
            "coins": coins,
            "sentiment": None,
            "lang": "en",
        })

    return results


def _normalize_naver(item: dict, coin_key: str) -> dict:
    """네이버 뉴스 API 응답 항목을 정규화한다.

    Args:
        item: 네이버 뉴스 API 원시 딕셔너리
        coin_key: 코인 키

    Returns:
        dict: 정규화된 뉴스 딕셔너리
    """
    title = _strip_html(item.get("title", ""))
    description = _strip_html(item.get("description", ""))
    pub_date = item.get("pubDate", "")
    coins = _extract_coins(f"{title} {description} {coin_key}")

    return {
        "title": title,
        "body": description,
        "url": item.get("originallink") or item.get("link", ""),
        "source": "Naver News",
        "published_at": _parse_rfc2822(pub_date),
        "categories": "Naver News",
        "coins": coins,
        "sentiment": None,
        "lang": "ko",
    }


def _tag_text(element: ET.Element, tag: str) -> str:
    """XML 요소에서 태그 텍스트를 안전하게 추출한다.

    Args:
        element: XML 요소
        tag: 태그명

    Returns:
        str: 태그 텍스트 (없으면 빈 문자열)
    """
    el = element.find(tag)
    return (el.text or "").strip() if el is not None else ""


def _strip_html(text: str) -> str:
    """HTML 태그를 제거하고 순수 텍스트를 반환한다.

    Args:
        text: HTML이 포함된 문자열

    Returns:
        str: HTML 태그가 제거된 문자열
    """
    import re
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _parse_rfc2822(date_str: str) -> Optional[str]:
    """RFC 2822 형식 날짜 문자열을 ISO 8601로 변환한다.

    Args:
        date_str: RFC 2822 형식 날짜 문자열 (예: 'Tue, 13 May 2026 10:00:00 +0900')

    Returns:
        str | None: ISO 8601 문자열 또는 None
    """
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def _extract_coins(text: str) -> list[str]:
    """텍스트에서 언급된 코인 심볼을 추출한다.

    Args:
        text: 분석할 텍스트

    Returns:
        list[str]: 코인 심볼 목록
    """
    mapping = {
        "BTC": ["BTC", "BITCOIN", "비트코인"],
        "ETH": ["ETH", "ETHEREUM", "이더리움"],
        "XRP": ["XRP", "RIPPLE", "리플"],
        "BNB": ["BNB", "BINANCE"],
        "SOL": ["SOL", "SOLANA", "솔라나"],
    }
    text_upper = text.upper()
    return [coin for coin, keywords in mapping.items() if any(k in text_upper for k in keywords)]
