# tests/test_db.py
# ============================================================
# 파일명  : test_db.py
# 버전    : V0p1
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p1  최초 작성 — Supabase client/queries 테스트 (mock 기반)
# ============================================================

import sys
import os
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.queries import (
    get_analysis_by_date,
    get_latest_news,
    get_news_by_date,
    get_prices_by_coin,
    insert_analysis,
    insert_news,
    insert_prices,
)


def _mock_client(return_data: list) -> MagicMock:
    """Supabase 클라이언트 Mock을 생성한다.

    매개변수:
        return_data: .execute() 반환값으로 설정할 데이터

    반환값:
        MagicMock: 설정된 클라이언트 Mock
    """
    execute_result = MagicMock()
    execute_result.data = return_data

    chain = MagicMock()
    chain.execute.return_value = execute_result
    chain.upsert.return_value = chain
    chain.insert.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.gte.return_value = chain
    chain.lt.return_value = chain
    chain.overlaps.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain

    client = MagicMock()
    client.table.return_value = chain
    return client


# ── insert_news 테스트 ───────────────────────────────────────

class TestInsertNews:
    def test_empty_list_returns_zero(self):
        client = _mock_client([])
        assert insert_news(client, []) == 0

    def test_returns_saved_count(self):
        saved = [{"id": "1"}, {"id": "2"}]
        client = _mock_client(saved)
        assert insert_news(client, [{"title": "T1"}, {"title": "T2"}]) == 2

    def test_none_data_returns_zero(self):
        client = _mock_client(None)
        # None data는 0 반환해야 함
        result = insert_news(client, [{"title": "Test"}])
        assert result == 0

    def test_table_called_with_crypto_news(self):
        client = _mock_client([{"id": "1"}])
        insert_news(client, [{"title": "News"}])
        client.table.assert_called_with("crypto_news")


# ── get_latest_news 테스트 ───────────────────────────────────

class TestGetLatestNews:
    def test_returns_list(self):
        news_data = [{"id": "1", "title": "BTC rally"}]
        client = _mock_client(news_data)
        result = get_latest_news(client, limit=10)
        assert result == news_data

    def test_empty_db_returns_empty_list(self):
        client = _mock_client(None)
        result = get_latest_news(client)
        assert result == []

    def test_table_called_correctly(self):
        client = _mock_client([])
        get_latest_news(client, limit=5)
        client.table.assert_called_with("crypto_news")


# ── get_news_by_date 테스트 ──────────────────────────────────

class TestGetNewsByDate:
    def test_returns_data(self):
        news_data = [{"id": "1", "title": "ETH upgrade"}]
        client = _mock_client(news_data)
        result = get_news_by_date(client, date(2026, 5, 13))
        assert result == news_data

    def test_none_coins_no_overlaps_filter(self):
        client = _mock_client([])
        get_news_by_date(client, date(2026, 5, 13), coins=None)
        # overlaps는 호출되지 않아야 함
        chain = client.table.return_value
        chain.overlaps.assert_not_called()


# ── insert_prices 테스트 ─────────────────────────────────────

class TestInsertPrices:
    def test_empty_list_returns_zero(self):
        client = _mock_client([])
        assert insert_prices(client, []) == 0

    def test_returns_saved_count(self):
        client = _mock_client([{"id": "1"}])
        assert insert_prices(client, [{"coin": "BTC", "price_usd": 65000}]) == 1


# ── get_prices_by_coin 테스트 ────────────────────────────────

class TestGetPricesByCoin:
    def test_returns_price_list(self):
        price_data = [{"coin": "BTC", "price_usd": 65000}]
        client = _mock_client(price_data)
        result = get_prices_by_coin(client, "BTC", days=7)
        assert result == price_data

    def test_empty_returns_empty_list(self):
        client = _mock_client(None)
        result = get_prices_by_coin(client, "ETH")
        assert result == []


# ── insert_analysis 테스트 ───────────────────────────────────

class TestInsertAnalysis:
    def test_success_returns_true(self):
        client = _mock_client([{"id": "1"}])
        assert insert_analysis(client, {"analysis_date": "2026-05-13", "coin": "BTC"}) is True

    def test_failure_returns_false(self):
        client = _mock_client(None)
        assert insert_analysis(client, {"coin": "BTC"}) is False


# ── get_analysis_by_date 테스트 ──────────────────────────────

class TestGetAnalysisByDate:
    def test_returns_analysis(self):
        analysis_data = [{"id": "1", "coin": "BTC", "summary": "Bullish"}]
        client = _mock_client(analysis_data)
        result = get_analysis_by_date(client, date(2026, 5, 13), "BTC")
        assert result == analysis_data

    def test_no_coin_filter(self):
        client = _mock_client([])
        get_analysis_by_date(client, date(2026, 5, 13), coin=None)
        chain = client.table.return_value
        chain.eq.assert_called_once()  # analysis_date eq만 호출됨


# ── Supabase 클라이언트 초기화 테스트 ────────────────────────

class TestGetSupabaseClient:
    def test_missing_env_raises_runtime_error(self):
        from src.db.client import get_supabase_client

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="환경변수"):
                get_supabase_client()

    def test_valid_env_creates_client(self):
        from src.db.client import get_supabase_client

        with patch.dict(
            os.environ,
            {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_ANON_KEY": "test-key"},
        ):
            with patch("src.db.client.create_client") as mock_create:
                mock_create.return_value = MagicMock()
                client = get_supabase_client()
                mock_create.assert_called_once_with(
                    "https://test.supabase.co", "test-key"
                )
