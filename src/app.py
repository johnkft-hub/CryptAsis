# src/app.py
# ============================================================
# 파일명  : app.py
# 버전    : V0p1
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p1  최초 작성 — Streamlit 크립토 뉴스/가격 대시보드
# ============================================================

from __future__ import annotations

import sys
import os
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

# 프로젝트 루트를 sys.path에 추가 (상대 임포트 대응)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from src.api.groq_client import analyze_news_price_correlation, summarize_daily_news
from src.api.news_client import fetch_crypto_news
from src.api.price_client import fetch_current_prices, fetch_price_history
from src.db.client import get_supabase_client
from src.db.queries import (
    get_analysis_by_date,
    get_latest_news,
    insert_analysis,
    insert_news,
    insert_prices,
)
from src.utils.helpers import (
    format_large_number,
    format_price_change,
    sentiment_to_emoji,
    today_kst,
    truncate_text,
)

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="CryptAsis — 크립토 뉴스 & 가격 상관관계",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

_COINS = ["BTC", "ETH"]
_COIN_NAMES = {"BTC": "Bitcoin (BTC)", "ETH": "Ethereum (ETH)"}
_COIN_COLORS = {"BTC": "#F7931A", "ETH": "#627EEA"}


# ── 캐시된 데이터 로드 함수 ──────────────────────────────────

@st.cache_data(ttl=300)
def load_current_prices() -> list[dict]:
    """실시간 BTC/ETH 가격을 가져온다 (5분 캐시).

    Returns:
        list[dict]: 가격 딕셔너리 목록
    """
    return fetch_current_prices(["BTC", "ETH"])


@st.cache_data(ttl=600)
def load_price_history(coin: str, days: int) -> list[dict]:
    """코인 가격 이력을 가져온다 (10분 캐시).

    Args:
        coin: 코인 심볼
        days: 조회 일수

    Returns:
        list[dict]: 가격 이력 딕셔너리 목록
    """
    return fetch_price_history(coin, days)


@st.cache_data(ttl=600)
def load_news(limit: int = 30) -> list[dict]:
    """최신 크립토 뉴스를 가져온다 (10분 캐시).

    Args:
        limit: 최대 뉴스 수

    Returns:
        list[dict]: 뉴스 딕셔너리 목록
    """
    return fetch_crypto_news(limit=limit)


def _get_db_client():
    """Supabase 클라이언트를 세션에서 재사용한다.

    Returns:
        Client | None: Supabase 클라이언트 또는 None (설정 오류 시)
    """
    if "db_client" not in st.session_state:
        try:
            st.session_state.db_client = get_supabase_client()
        except RuntimeError:
            st.session_state.db_client = None
    return st.session_state.db_client


# ── UI 컴포넌트 ──────────────────────────────────────────────

def render_price_metrics(prices: list[dict]) -> None:
    """가격 지표 카드를 렌더링한다.

    Args:
        prices: 가격 딕셔너리 목록
    """
    price_map = {p["coin"]: p for p in prices}
    cols = st.columns(len(_COINS) * 2)

    for i, coin in enumerate(_COINS):
        data = price_map.get(coin, {})
        price = data.get("price_usd", 0) or 0
        change_24h = data.get("change_24h", 0) or 0
        change_7d = data.get("change_7d", 0) or 0
        market_cap = data.get("market_cap")
        volume = data.get("volume_24h")

        with cols[i * 2]:
            st.metric(
                label=f"💰 {_COIN_NAMES[coin]}",
                value=f"${price:,.2f}",
                delta=f"{change_24h:+.2f}% (24h)",
            )
            st.caption(f"시가총액: {format_large_number(market_cap)}")

        with cols[i * 2 + 1]:
            st.metric(
                label="7일 변동",
                value=format_price_change(change_7d),
                delta=f"거래량: {format_large_number(volume)}",
                delta_color="off",
            )


def render_price_chart(coin: str, days: int) -> None:
    """코인 가격 이력 차트를 렌더링한다.

    Args:
        coin: 코인 심볼
        days: 표시할 일수
    """
    with st.spinner(f"{coin} 가격 이력 로딩 중..."):
        history = load_price_history(coin, days)

    if not history:
        st.warning(f"{coin} 가격 이력 데이터를 가져오지 못했습니다.")
        return

    df = pd.DataFrame(history)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["price_usd"],
            mode="lines+markers",
            name=coin,
            line={"color": _COIN_COLORS.get(coin, "#888"), "width": 2},
            marker={"size": 4},
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>$%{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=f"{_COIN_NAMES.get(coin, coin)} 가격 ({days}일)",
        xaxis_title="날짜",
        yaxis_title="가격 (USD)",
        height=350,
        margin={"t": 40, "b": 20, "l": 0, "r": 0},
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_news_list(news_list: list[dict], coin_filter: str | None = None) -> None:
    """뉴스 목록을 카드 형태로 렌더링한다.

    Args:
        news_list: 뉴스 딕셔너리 목록
        coin_filter: 필터링할 코인 심볼. None이면 전체 표시
    """
    if coin_filter:
        filtered = [
            n for n in news_list if coin_filter in (n.get("coins") or [])
        ]
    else:
        filtered = news_list

    if not filtered:
        st.info("표시할 뉴스가 없습니다.")
        return

    for news in filtered[:15]:
        coins = news.get("coins") or []
        coin_tags = " ".join([f"`{c}`" for c in coins]) if coins else ""
        published = news.get("published_at", "")[:10] if news.get("published_at") else ""

        with st.expander(f"📰 {news.get('title', '제목 없음')} {coin_tags}"):
            st.caption(f"출처: {news.get('source', '-')} | 게시: {published}")
            body = truncate_text(news.get("body", "") or "", 400)
            if body:
                st.write(body)
            if news.get("url"):
                st.markdown(f"[원문 보기 →]({news['url']})")


def render_ai_analysis(
    coin: str,
    news_list: list[dict],
    price_data: dict,
    analysis_date: str,
) -> None:
    """AI 상관관계 분석 결과를 렌더링한다.

    Args:
        coin: 코인 심볼
        news_list: 뉴스 목록
        price_data: 가격 딕셔너리
        analysis_date: 분석 날짜
    """
    db = _get_db_client()

    # DB에서 기존 분석 결과 조회
    if db:
        existing = get_analysis_by_date(db, date.fromisoformat(analysis_date), coin)
        if existing:
            st.success("저장된 분석 결과를 불러왔습니다.")
            _display_analysis_result(existing[0])
            return

    if not news_list:
        st.warning("분석할 뉴스가 없습니다. 먼저 뉴스를 수집하세요.")
        return

    col1, col2 = st.columns([3, 1])
    with col2:
        if not st.button(f"🤖 {coin} AI 분석 실행", type="primary"):
            st.info("버튼을 눌러 AI 분석을 시작하세요.")
            return

    with st.spinner(f"Groq AI가 {coin} 뉴스-가격 상관관계 분석 중..."):
        try:
            result = analyze_news_price_correlation(
                coin, news_list, price_data, analysis_date
            )
        except RuntimeError as e:
            st.error(f"AI 분석 오류: {e}")
            return

    _display_analysis_result(result)

    if db:
        insert_analysis(
            db,
            {
                "analysis_date": analysis_date,
                "coin": coin,
                **result,
            },
        )
        st.caption("분석 결과가 DB에 저장되었습니다.")


def _display_analysis_result(result: dict) -> None:
    """분석 결과 딕셔너리를 화면에 출력한다.

    Args:
        result: 분석 결과 딕셔너리
    """
    sentiment = result.get("sentiment", "neutral")
    st.subheader(f"센티멘트: {sentiment_to_emoji(sentiment)}")

    raw = result.get("raw_response", "")
    if raw:
        st.markdown(raw)
    else:
        st.write(result.get("summary", "분석 결과 없음"))


# ── 메인 레이아웃 ────────────────────────────────────────────

def main() -> None:
    """Streamlit 앱 진입점."""
    st.title("📊 CryptAsis — 크립토 뉴스 & 가격 상관관계 분석기")
    st.caption(
        "Bitcoin(BTC) · Ethereum(ETH) 최신 뉴스를 수집하고 "
        "Groq AI가 가격 변화와의 상관관계를 분석합니다."
    )

    # ── 사이드바 ──
    with st.sidebar:
        st.header("⚙️ 설정")
        selected_coin = st.selectbox("분석 코인 선택", _COINS, format_func=lambda c: _COIN_NAMES[c])
        history_days = st.slider("가격 이력 조회 일수", 3, 30, 7)
        news_limit = st.slider("뉴스 수집 건수", 10, 50, 30)
        analysis_date = st.date_input("분석 날짜", value=today_kst())

        st.divider()
        st.subheader("🔄 데이터 갱신")

        if st.button("뉴스 & 가격 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        if st.button("뉴스 DB 저장", use_container_width=True):
            _save_news_to_db(news_limit)

        st.divider()
        _render_sidebar_info()

    # ── 가격 지표 ──
    st.header("💹 실시간 가격")
    with st.spinner("가격 데이터 로딩 중..."):
        try:
            prices = load_current_prices()
        except Exception as e:
            st.error(f"가격 데이터 로드 실패: {e}")
            prices = []

    if prices:
        render_price_metrics(prices)
        price_map = {p["coin"]: p for p in prices}
    else:
        price_map = {}

    st.divider()

    # ── 가격 차트 ──
    st.header(f"📈 {_COIN_NAMES[selected_coin]} 가격 이력")
    render_price_chart(selected_coin, history_days)

    st.divider()

    # ── 뉴스 탭 ──
    st.header("📰 크립토 뉴스")
    with st.spinner("뉴스 수집 중..."):
        try:
            news_list = load_news(news_limit)
        except Exception as e:
            st.error(f"뉴스 로드 실패: {e}")
            news_list = []

    tab_all, tab_btc, tab_eth = st.tabs(["전체", "Bitcoin (BTC)", "Ethereum (ETH)"])
    with tab_all:
        render_news_list(news_list)
    with tab_btc:
        render_news_list(news_list, "BTC")
    with tab_eth:
        render_news_list(news_list, "ETH")

    st.divider()

    # ── AI 분석 ──
    st.header(f"🤖 {_COIN_NAMES[selected_coin]} AI 뉴스-가격 상관관계 분석")
    coin_news = [n for n in news_list if selected_coin in (n.get("coins") or [])]
    if not coin_news:
        coin_news = news_list

    render_ai_analysis(
        selected_coin,
        coin_news,
        price_map.get(selected_coin, {}),
        analysis_date.isoformat(),
    )

    st.divider()

    # ── 일일 뉴스 요약 ──
    st.header("📋 일일 뉴스 AI 요약")
    if st.button("뉴스 요약 생성", use_container_width=False):
        with st.spinner("Groq AI가 뉴스 전체 요약 중..."):
            try:
                summary = summarize_daily_news(news_list, analysis_date.isoformat())
                st.markdown(summary)
            except RuntimeError as e:
                st.error(f"요약 오류: {e}")


def _save_news_to_db(limit: int) -> None:
    """뉴스를 수집하여 Supabase DB에 저장한다.

    Args:
        limit: 저장할 최대 뉴스 수
    """
    db = _get_db_client()
    if not db:
        st.sidebar.error("Supabase 연결 실패. .env를 확인하세요.")
        return

    with st.sidebar.spinner("뉴스 저장 중..."):
        try:
            news = fetch_crypto_news(limit=limit)
            saved = insert_news(db, news)
            st.sidebar.success(f"{saved}건 저장 완료")
        except Exception as e:
            st.sidebar.error(f"저장 오류: {e}")


def _render_sidebar_info() -> None:
    """사이드바 하단 앱 정보를 렌더링한다."""
    st.caption(
        "**CryptAsis v0.1**\n\n"
        "뉴스: CryptoCompare API\n"
        "가격: CoinGecko API\n"
        "AI: Groq llama-3.3-70b\n"
        "DB: Supabase\n\n"
        "⚠️ 투자 권유가 아닌 정보 제공 목적입니다."
    )


if __name__ == "__main__":
    main()
