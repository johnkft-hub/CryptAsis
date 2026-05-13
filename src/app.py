# src/app.py
# ============================================================
# 파일명  : app.py
# 버전    : V0p2
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p1  최초 작성 — Streamlit 크립토 뉴스/가격 대시보드
# 2026-05-13  V0p2  뉴스 통계 탭 추가 (일별 관리 + 누적 비교)
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
    get_news_for_stats,
    get_news_total_count,
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
_COIN_NAMES = {"BTC": "비트코인 (BTC)", "ETH": "이더리움 (ETH)"}
_COIN_COLORS = {"BTC": "#F7931A", "ETH": "#627EEA"}


# ── 캐시된 데이터 로드 함수 ──────────────────────────────────

@st.cache_data(ttl=300)
def load_current_prices() -> list[dict]:
    """실시간 BTC/ETH 가격을 가져온다 (5분 캐시).

    반환값:
        list[dict]: 가격 딕셔너리 목록
    """
    return fetch_current_prices(["BTC", "ETH"])


@st.cache_data(ttl=600)
def load_price_history(coin: str, days: int) -> list[dict]:
    """코인 가격 이력을 가져온다 (10분 캐시).

    매개변수:
        coin: 코인 심볼
        days: 조회 일수

    반환값:
        list[dict]: 가격 이력 딕셔너리 목록
    """
    return fetch_price_history(coin, days)


@st.cache_data(ttl=600)
def load_news(limit: int = 30) -> list[dict]:
    """최신 크립토 뉴스를 가져온다 (10분 캐시).

    매개변수:
        limit: 최대 뉴스 수

    반환값:
        list[dict]: 뉴스 딕셔너리 목록
    """
    return fetch_crypto_news(limit=limit)


def _get_db_client():
    """Supabase 클라이언트를 세션에서 재사용한다.

    반환값:
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

    매개변수:
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

    매개변수:
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

    매개변수:
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

    매개변수:
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

    매개변수:
        result: 분석 결과 딕셔너리
    """
    sentiment = result.get("sentiment", "neutral")
    st.subheader(f"센티멘트: {sentiment_to_emoji(sentiment)}")

    raw = result.get("raw_response", "")
    if raw:
        st.markdown(raw)
    else:
        st.write(result.get("summary", "분석 결과 없음"))


# ── 뉴스 통계 ────────────────────────────────────────────────

def render_news_stats(db) -> None:
    """뉴스 수집 통계 탭을 렌더링한다 (일별 관리 + 누적 비교).

    매개변수:
        db: Supabase 클라이언트 (None이면 안내 메시지 표시)
    """
    if not db:
        st.warning("DB 연결이 필요합니다. .env의 Supabase 설정을 확인하세요.")
        return

    # ── 통계 기간 선택 ──
    stat_days = st.slider("통계 조회 기간 (일)", 7, 90, 30, key="stat_days")

    with st.spinner("DB에서 통계 데이터 로딩 중..."):
        raw = get_news_for_stats(db, days=stat_days)
        total = get_news_total_count(db)

    if not raw:
        st.info("저장된 뉴스 데이터가 없습니다. 사이드바의 '뉴스 DB 저장' 버튼을 먼저 실행하세요.")
        return

    df = _build_stats_df(raw)

    # ── 상단 요약 지표 ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("DB 전체 누적", f"{total:,} 건")
    with col2:
        st.metric(f"최근 {stat_days}일 수집", f"{len(df):,} 건")
    with col3:
        naver_cnt = int((df["source"] == "네이버 뉴스").sum())
        st.metric("네이버 뉴스", f"{naver_cnt:,} 건")
    with col4:
        google_cnt = int((df["source"] == "구글 뉴스").sum())
        st.metric("구글 뉴스", f"{google_cnt:,} 건")

    st.divider()

    # ── 탭 구성 ──
    tab_daily, tab_cumul, tab_source, tab_coin = st.tabs(
        ["📅 일별 수집 현황", "📈 누적 데이터 비교", "🌐 소스별 비교", "🪙 코인별 비교"]
    )

    with tab_daily:
        _render_daily_tab(df)

    with tab_cumul:
        _render_cumulative_tab(df)

    with tab_source:
        _render_source_tab(df)

    with tab_coin:
        _render_coin_tab(df)


def _build_stats_df(raw: list[dict]) -> pd.DataFrame:
    """raw 뉴스 데이터를 통계용 DataFrame으로 변환한다.

    매개변수:
        raw: DB에서 조회한 뉴스 딕셔너리 목록

    반환값:
        pd.DataFrame: 날짜/소스/코인 컬럼이 정리된 DataFrame
    """
    df = pd.DataFrame(raw)
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    df["date"] = df["created_at"].dt.date
    df["source"] = df["source"].fillna("기타")
    # source를 네이버/구글/기타 3가지로 정규화
    df["source"] = df["source"].apply(
        lambda s: "네이버 뉴스" if "naver" in s.lower() or "네이버" in s
        else ("구글 뉴스" if "google" in s.lower() or "구글" in s else "기타")
    )
    # coins 컬럼(list)에서 BTC/ETH 여부 추출
    df["has_btc"] = df["coins"].apply(lambda c: "BTC" in (c or []))
    df["has_eth"] = df["coins"].apply(lambda c: "ETH" in (c or []))
    return df


def _render_daily_tab(df: pd.DataFrame) -> None:
    """일별 수집 현황 차트를 렌더링한다.

    매개변수:
        df: 통계용 DataFrame
    """
    st.subheader("일별 뉴스 수집 건수")

    daily = (
        df.groupby(["date", "source"])
        .size()
        .reset_index(name="count")
    )

    sources = daily["source"].unique()
    colors = {"네이버 뉴스": "#03C75A", "구글 뉴스": "#4285F4", "기타": "#888888"}

    fig = go.Figure()
    for src in sources:
        d = daily[daily["source"] == src]
        fig.add_trace(go.Bar(
            x=d["date"].astype(str),
            y=d["count"],
            name=src,
            marker_color=colors.get(src, "#888"),
            hovertemplate="<b>%{x}</b><br>%{y}건<extra>" + src + "</extra>",
        ))

    fig.update_layout(
        barmode="stack",
        xaxis_title="날짜",
        yaxis_title="수집 건수",
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin={"t": 40, "b": 20, "l": 0, "r": 0},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    # 일별 요약 테이블
    st.subheader("일별 수집 내역")
    pivot = (
        df.groupby(["date", "source"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    pivot["합계"] = pivot.select_dtypes("number").sum(axis=1)
    pivot = pivot.sort_values("date", ascending=False).rename(columns={"date": "날짜"})
    st.dataframe(pivot, use_container_width=True, hide_index=True)


def _render_cumulative_tab(df: pd.DataFrame) -> None:
    """누적 뉴스 수집 비교 차트를 렌더링한다.

    매개변수:
        df: 통계용 DataFrame
    """
    st.subheader("누적 뉴스 수집 추이")

    daily_total = df.groupby("date").size().reset_index(name="daily")
    daily_total = daily_total.sort_values("date")
    daily_total["누적"] = daily_total["daily"].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_total["date"].astype(str),
        y=daily_total["누적"],
        mode="lines+markers",
        name="누적 수집",
        fill="tozeroy",
        fillcolor="rgba(247,147,26,0.15)",
        line={"color": "#F7931A", "width": 2},
        hovertemplate="<b>%{x}</b><br>누적 %{y}건<extra></extra>",
    ))

    fig.update_layout(
        xaxis_title="날짜",
        yaxis_title="누적 건수",
        height=350,
        margin={"t": 30, "b": 20, "l": 0, "r": 0},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    # 네이버 vs 구글 누적 비교
    st.subheader("소스별 누적 비교")
    for src, color in [("네이버 뉴스", "#03C75A"), ("구글 뉴스", "#4285F4")]:
        src_df = df[df["source"] == src].groupby("date").size().reset_index(name="daily")
        src_df = src_df.sort_values("date")
        src_df["누적"] = src_df["daily"].cumsum()

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=src_df["date"].astype(str),
            y=src_df["누적"],
            mode="lines+markers",
            name=src,
            line={"color": color, "width": 2},
            hovertemplate=f"<b>%{{x}}</b><br>{src} 누적 %{{y}}건<extra></extra>",
        ))
        fig2.update_layout(
            title=src,
            height=250,
            margin={"t": 30, "b": 10, "l": 0, "r": 0},
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)


def _render_source_tab(df: pd.DataFrame) -> None:
    """소스별(네이버/구글) 뉴스 비교 차트를 렌더링한다.

    매개변수:
        df: 통계용 DataFrame
    """
    st.subheader("뉴스 소스별 비중")

    source_counts = df["source"].value_counts().reset_index()
    source_counts.columns = ["소스", "건수"]

    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure(go.Pie(
            labels=source_counts["소스"],
            values=source_counts["건수"],
            hole=0.45,
            marker_colors=["#03C75A", "#4285F4", "#888888"],
            hovertemplate="<b>%{label}</b><br>%{value}건 (%{percent})<extra></extra>",
        ))
        fig.update_layout(
            title="소스별 비중",
            height=320,
            margin={"t": 40, "b": 0, "l": 0, "r": 0},
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.dataframe(
            source_counts,
            use_container_width=True,
            hide_index=True,
        )
        st.caption("일별 소스 추이")
        daily_src = df.groupby(["date", "source"]).size().unstack(fill_value=0).reset_index()
        daily_src = daily_src.sort_values("date", ascending=False).head(10)
        st.dataframe(daily_src, use_container_width=True, hide_index=True)


def _render_coin_tab(df: pd.DataFrame) -> None:
    """코인별(BTC/ETH) 뉴스 비교 차트를 렌더링한다.

    매개변수:
        df: 통계용 DataFrame
    """
    st.subheader("코인별 언급 뉴스 추이")

    daily_coin = df.groupby("date").agg(
        BTC=("has_btc", "sum"),
        ETH=("has_eth", "sum"),
    ).reset_index().sort_values("date")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_coin["date"].astype(str),
        y=daily_coin["BTC"],
        mode="lines+markers",
        name="비트코인 (BTC)",
        line={"color": "#F7931A", "width": 2},
        hovertemplate="<b>%{x}</b><br>BTC %{y}건<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=daily_coin["date"].astype(str),
        y=daily_coin["ETH"],
        mode="lines+markers",
        name="이더리움 (ETH)",
        line={"color": "#627EEA", "width": 2},
        hovertemplate="<b>%{x}</b><br>ETH %{y}건<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="날짜",
        yaxis_title="언급 건수",
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin={"t": 30, "b": 20, "l": 0, "r": 0},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    # BTC vs ETH 총계 비교
    col1, col2 = st.columns(2)
    with col1:
        btc_total = int(df["has_btc"].sum())
        st.metric("비트코인 (BTC) 언급", f"{btc_total:,} 건")
    with col2:
        eth_total = int(df["has_eth"].sum())
        st.metric("이더리움 (ETH) 언급", f"{eth_total:,} 건")


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

    tab_all, tab_btc, tab_eth = st.tabs(["전체", "비트코인 (BTC)", "이더리움 (ETH)"])
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

    st.divider()

    # ── 뉴스 통계 ──
    st.header("📊 뉴스 수집 통계")
    render_news_stats(_get_db_client())


def _save_news_to_db(limit: int) -> None:
    """뉴스를 수집하여 Supabase DB에 저장한다.

    매개변수:
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
        "뉴스: 네이버 뉴스 API + 구글 뉴스 RSS\n"
        "가격: CoinGecko API\n"
        "AI: Groq llama-3.3-70b\n"
        "DB: Supabase\n\n"
        "⚠️ 투자 권유가 아닌 정보 제공 목적입니다."
    )


if __name__ == "__main__":
    main()
