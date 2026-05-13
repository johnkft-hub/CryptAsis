# src/api/price_client.py
# ============================================================
# 파일명  : price_client.py
# 버전    : V0p1
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p1  최초 작성 — CoinGecko API 연동
# ============================================================

import ssl
import requests

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

_BASE_URL = "https://api.coingecko.com/api/v3"
_SSL_VERIFY = True

_COIN_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "XRP": "ripple",
    "BNB": "binancecoin",
    "SOL": "solana",
}


def fetch_current_prices(coins: list[str] = None) -> list[dict]:
    """CoinGecko에서 실시간 가격 데이터를 가져온다.

    Args:
        coins: 조회할 코인 심볼 목록 (예: ['BTC', 'ETH']). None이면 BTC/ETH

    Returns:
        list[dict]: 정규화된 가격 딕셔너리 목록

    Raises:
        requests.HTTPError: API 오류 시
    """
    if coins is None:
        coins = ["BTC", "ETH"]

    coin_ids = [_COIN_ID_MAP[c] for c in coins if c in _COIN_ID_MAP]
    if not coin_ids:
        return []

    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": "usd",
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
        "include_last_updated_at": "true",
        "price_change_percentage": "1h,24h,7d",
    }

    response = requests.get(
        f"{_BASE_URL}/coins/markets",
        params={
            "vs_currency": "usd",
            "ids": ",".join(coin_ids),
            "price_change_percentage": "1h,24h,7d",
            "order": "market_cap_desc",
            "per_page": 10,
            "page": 1,
        },
        timeout=10,
        verify=_SSL_VERIFY,
    )
    response.raise_for_status()

    id_to_symbol = {v: k for k, v in _COIN_ID_MAP.items()}
    return [_normalize_price(item, id_to_symbol) for item in response.json()]


def fetch_price_history(coin: str, days: int = 7) -> list[dict]:
    """CoinGecko에서 코인의 가격 이력을 가져온다.

    Args:
        coin: 코인 심볼 (예: 'BTC', 'ETH')
        days: 조회할 일수 (1~365)

    Returns:
        list[dict]: {'timestamp': str, 'price_usd': float} 딕셔너리 목록

    Raises:
        ValueError: 지원하지 않는 코인 심볼
        requests.HTTPError: API 오류 시
    """
    coin_id = _COIN_ID_MAP.get(coin)
    if not coin_id:
        raise ValueError(f"지원하지 않는 코인 심볼: {coin}")

    response = requests.get(
        f"{_BASE_URL}/coins/{coin_id}/market_chart",
        params={"vs_currency": "usd", "days": days, "interval": "daily"},
        timeout=10,
        verify=_SSL_VERIFY,
    )
    response.raise_for_status()

    prices = response.json().get("prices", [])
    return [
        {
            "coin": coin,
            "timestamp": _ms_to_iso(ts),
            "price_usd": price,
        }
        for ts, price in prices
    ]


def _normalize_price(item: dict, id_to_symbol: dict) -> dict:
    """CoinGecko markets 응답을 DB 저장 형식으로 변환한다.

    Args:
        item: CoinGecko 원시 가격 딕셔너리
        id_to_symbol: coingecko_id -> 심볼 매핑

    Returns:
        dict: 정규화된 가격 딕셔너리
    """
    coin_id = item.get("id", "")
    symbol = id_to_symbol.get(coin_id, coin_id.upper())

    return {
        "coin": symbol,
        "price_usd": item.get("current_price"),
        "change_1h": item.get("price_change_percentage_1h_in_currency"),
        "change_24h": item.get("price_change_percentage_24h_in_currency"),
        "change_7d": item.get("price_change_percentage_7d_in_currency"),
        "market_cap": item.get("market_cap"),
        "volume_24h": item.get("total_volume"),
    }


def _ms_to_iso(ms_timestamp: int) -> str:
    """밀리초 타임스탬프를 ISO 8601 문자열로 변환한다.

    Args:
        ms_timestamp: 밀리초 단위 UNIX 타임스탬프

    Returns:
        str: ISO 8601 형식 문자열 (UTC)
    """
    from datetime import datetime, timezone

    return datetime.fromtimestamp(ms_timestamp / 1000, tz=timezone.utc).isoformat()
