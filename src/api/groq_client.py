# src/api/groq_client.py
# ============================================================
# 파일명  : groq_client.py
# 버전    : V0p1
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p1  최초 작성 — Groq llama-3.3-70b 분석 연동
# ============================================================

from groq import Groq

from src.api.prompts import build_correlation_prompt, build_summary_prompt
from src.utils.config import get_groq_api_key

_MODEL = "llama-3.3-70b-versatile"
_MAX_TOKENS = 2048


def _get_client() -> Groq:
    """Groq 클라이언트를 초기화하여 반환한다.

    로컬: .env의 GROQ_API_KEY 사용
    클라우드: Streamlit secrets 사용

    Returns:
        Groq: 초기화된 Groq 클라이언트

    Raises:
        RuntimeError: API 키 미설정 시
    """
    return Groq(api_key=get_groq_api_key())


def analyze_news_price_correlation(
    coin: str,
    news_list: list[dict],
    price_data: dict,
    analysis_date: str,
) -> dict:
    """뉴스와 가격 데이터의 상관관계를 Groq AI로 분석한다.

    Args:
        coin: 분석 대상 코인 심볼 (예: 'BTC', 'ETH')
        news_list: 뉴스 딕셔너리 목록
        price_data: 가격 딕셔너리
        analysis_date: 분석 날짜 문자열 (YYYY-MM-DD)

    Returns:
        dict: {
            'summary': str,           # 전체 분석 텍스트
            'sentiment': str,         # 'positive' | 'negative' | 'neutral'
            'price_impact': str,      # 가격 영향 요약
            'key_factors': str,       # 핵심 요인
            'raw_response': str,      # AI 원문 응답
        }

    Raises:
        RuntimeError: API 키 미설정 시
    """
    client = _get_client()
    prompt = build_correlation_prompt(coin, news_list, price_data, analysis_date)

    completion = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 암호화폐 시장 분석 전문가입니다. "
                    "뉴스와 가격 데이터를 기반으로 객관적이고 구체적인 분석을 제공합니다. "
                    "투자 권유가 아닌 정보 제공 목적임을 항상 명시하세요."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=_MAX_TOKENS,
        temperature=0.3,
    )

    raw_response = completion.choices[0].message.content or ""
    return _parse_analysis_response(raw_response, coin)


def summarize_daily_news(news_list: list[dict], analysis_date: str) -> str:
    """일일 뉴스를 Groq AI로 요약한다.

    Args:
        news_list: 뉴스 딕셔너리 목록
        analysis_date: 분석 날짜 문자열 (YYYY-MM-DD)

    Returns:
        str: 요약 텍스트

    Raises:
        RuntimeError: API 키 미설정 시
    """
    client = _get_client()
    prompt = build_summary_prompt(news_list, analysis_date)

    completion = client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.3,
    )

    return completion.choices[0].message.content or ""


def _parse_analysis_response(raw: str, coin: str) -> dict:
    """AI 분석 원문 텍스트를 구조화된 딕셔너리로 변환한다.

    Args:
        raw: AI 원문 응답 텍스트
        coin: 분석 대상 코인 심볼

    Returns:
        dict: 파싱된 분석 딕셔너리
    """
    raw_lower = raw.lower()
    if any(w in raw_lower for w in ["긍정", "상승", "호재", "positive", "bullish"]):
        sentiment = "positive"
    elif any(w in raw_lower for w in ["부정", "하락", "악재", "negative", "bearish"]):
        sentiment = "negative"
    else:
        sentiment = "neutral"

    lines = raw.split("\n")
    price_impact_lines = []
    key_factor_lines = []

    in_price = False
    in_factors = False
    for line in lines:
        if "가격에 미친" in line or "price" in line.lower():
            in_price = True
            in_factors = False
        elif "핵심" in line or "주요 요인" in line or "key" in line.lower():
            in_price = False
            in_factors = True
        elif line.startswith("##") or line.startswith("**") and "." in line:
            in_price = False
            in_factors = False

        if in_price and line.strip():
            price_impact_lines.append(line.strip())
        if in_factors and line.strip():
            key_factor_lines.append(line.strip())

    return {
        "summary": raw[:500] if len(raw) > 500 else raw,
        "sentiment": sentiment,
        "price_impact": "\n".join(price_impact_lines[:5]) or raw[:200],
        "key_factors": "\n".join(key_factor_lines[:5]) or "",
        "raw_response": raw,
    }
