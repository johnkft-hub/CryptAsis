# tests/test_api.py
# ============================================================
# 파일명  : test_api.py
# 버전    : V0p1
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p1  최초 작성 — news_client, price_client, groq_client 테스트
# ============================================================

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.news_client import _extract_coins, _normalize_news
from src.api.price_client import _ms_to_iso, _normalize_price
from src.api.prompts import (
    _format_price_section,
    build_correlation_prompt,
    build_summary_prompt,
)
from src.utils.helpers import (
    format_large_number,
    format_price_change,
    sentiment_to_emoji,
    truncate_text,
)


# ── news_client 테스트 ───────────────────────────────────────

class TestExtractCoins:
    def test_btc_eth_detected(self):
        assert set(_extract_coins("BTC ETH")) == {"BTC", "ETH"}

    def test_no_coin(self):
        assert _extract_coins("general market news") == []

    def test_case_insensitive(self):
        assert "BTC" in _extract_coins("bitcoin btc rally")

    def test_unknown_coin_ignored(self):
        result = _extract_coins("FAKECOIN news")
        assert "FAKECOIN" not in result


class TestNormalizeNews:
    def test_basic_fields_present(self):
        raw = {
            "title": "BTC hits 100k",
            "body": "Bitcoin reaches milestone...",
            "url": "https://example.com/news/1",
            "source_info": {"name": "CoinDesk"},
            "published_on": 1715000000,
            "categories": "BTC",
            "tags": "Bitcoin",
        }
        result = _normalize_news(raw)
        assert result["title"] == "BTC hits 100k"
        assert result["url"] == "https://example.com/news/1"
        assert result["source"] == "CoinDesk"
        assert "BTC" in result["coins"]
        assert result["published_at"] is not None

    def test_missing_fields_graceful(self):
        result = _normalize_news({})
        assert result["title"] == ""
        assert result["coins"] == []
        assert result["sentiment"] is None

    def test_published_at_zero_returns_none(self):
        result = _normalize_news({"published_on": 0})
        assert result["published_at"] is None


# ── price_client 테스트 ──────────────────────────────────────

class TestMsToIso:
    def test_conversion(self):
        iso = _ms_to_iso(1715000000000)
        assert iso.startswith("2024-")
        assert "T" in iso

    def test_zero_timestamp(self):
        iso = _ms_to_iso(0)
        assert "1970" in iso


class TestNormalizePrice:
    def test_basic_fields(self):
        raw = {
            "id": "bitcoin",
            "current_price": 65000,
            "price_change_percentage_1h_in_currency": 0.5,
            "price_change_percentage_24h_in_currency": -2.1,
            "price_change_percentage_7d_in_currency": 5.3,
            "market_cap": 1_280_000_000_000,
            "total_volume": 45_000_000_000,
        }
        id_to_symbol = {"bitcoin": "BTC"}
        result = _normalize_price(raw, id_to_symbol)

        assert result["coin"] == "BTC"
        assert result["price_usd"] == 65000
        assert result["change_24h"] == -2.1
        assert result["market_cap"] == 1_280_000_000_000

    def test_unknown_coin_uses_id(self):
        raw = {"id": "unknowncoin", "current_price": 1}
        result = _normalize_price(raw, {})
        assert result["coin"] == "UNKNOWNCOIN"


# ── prompts 테스트 ───────────────────────────────────────────

class TestBuildCorrelationPrompt:
    def test_contains_coin_and_date(self):
        prompt = build_correlation_prompt(
            "BTC",
            [{"title": "BTC news", "body": "body", "source": "CoinDesk"}],
            {"price_usd": 65000, "change_24h": 1.5, "change_7d": 5.0},
            "2026-05-13",
        )
        assert "BTC" in prompt
        assert "2026-05-13" in prompt
        assert "65,000.00" in prompt

    def test_empty_news_handled(self):
        prompt = build_correlation_prompt("ETH", [], {}, "2026-05-13")
        assert "수집된 뉴스가 없습니다" in prompt


class TestBuildSummaryPrompt:
    def test_contains_date(self):
        prompt = build_summary_prompt([], "2026-05-13")
        assert "2026-05-13" in prompt

    def test_news_count_in_prompt(self):
        news = [{"title": f"News {i}", "body": "", "source": ""} for i in range(5)]
        prompt = build_summary_prompt(news, "2026-05-13")
        assert "5건" in prompt


class TestFormatPriceSection:
    def test_positive_change(self):
        section = _format_price_section("BTC", {"price_usd": 65000, "change_24h": 2.5, "change_7d": 5.0})
        assert "▲" in section
        assert "65,000.00" in section

    def test_negative_change(self):
        section = _format_price_section("ETH", {"price_usd": 3000, "change_24h": -1.3, "change_7d": -3.0})
        assert "▼" in section

    def test_empty_data(self):
        section = _format_price_section("BTC", {})
        assert "없음" in section


# ── helpers 테스트 ───────────────────────────────────────────

class TestFormatPriceChange:
    def test_positive(self):
        assert "▲" in format_price_change(2.5)
        assert "2.50%" in format_price_change(2.5)

    def test_negative(self):
        assert "▼" in format_price_change(-1.3)

    def test_none_returns_dash(self):
        assert format_price_change(None) == "-"

    def test_zero_is_positive_arrow(self):
        assert "▲" in format_price_change(0.0)


class TestFormatLargeNumber:
    def test_trillion(self):
        assert "T" in format_large_number(1_500_000_000_000)

    def test_billion(self):
        assert "B" in format_large_number(45_000_000_000)

    def test_million(self):
        assert "M" in format_large_number(5_000_000)

    def test_small(self):
        result = format_large_number(500)
        assert "$500.00" in result

    def test_none_returns_dash(self):
        assert format_large_number(None) == "-"

    def test_custom_prefix(self):
        assert "€" in format_large_number(1_000_000, prefix="€")


class TestSentimentToEmoji:
    def test_positive(self):
        assert "긍정" in sentiment_to_emoji("positive")

    def test_negative(self):
        assert "부정" in sentiment_to_emoji("negative")

    def test_neutral(self):
        assert "중립" in sentiment_to_emoji("neutral")

    def test_unknown(self):
        result = sentiment_to_emoji("unknown")
        assert "알 수 없음" in result

    def test_none(self):
        assert sentiment_to_emoji(None) != ""


class TestTruncateText:
    def test_short_text_unchanged(self):
        assert truncate_text("hello", 100) == "hello"

    def test_long_text_truncated(self):
        text = "a" * 200
        result = truncate_text(text, 100)
        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")

    def test_empty_string(self):
        assert truncate_text("") == ""
