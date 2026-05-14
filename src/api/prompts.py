# src/api/prompts.py
# ============================================================
# 파일명  : prompts.py
# 버전    : V0p1
# 작성일  : 2026-05-13
# 작성자  : johnkft-hub
#
# [변경 이력]
# 2026-05-13  V0p1  최초 작성 — 뉴스-가격 상관관계 분석 프롬프트
# ============================================================


def build_correlation_prompt(
    coin: str,
    news_list: list[dict],
    price_data: dict,
    analysis_date: str,
) -> str:
    """뉴스-가격 상관관계 분석을 위한 Groq 프롬프트를 생성한다.

    매개변수:
        coin: 분석 대상 코인 심볼 (예: 'BTC', 'ETH')
        news_list: 뉴스 딕셔너리 목록 (title, body, source 포함)
        price_data: 가격 딕셔너리 (price_usd, change_24h, change_7d 포함)
        analysis_date: 분석 날짜 문자열 (YYYY-MM-DD)

    반환값:
        str: Groq API에 전달할 프롬프트 문자열
    """
    news_section = _format_news_section(news_list)
    price_section = _format_price_section(coin, price_data)

    return f"""당신은 암호화폐 시장 분석 전문가입니다.
아래 {analysis_date} 기준 {coin} 관련 뉴스와 가격 데이터를 분석하세요.

## 가격 데이터
{price_section}

## 최신 뉴스 ({len(news_list)}건)
{news_section}

## 분석 요청
다음 항목을 한국어로 명확하게 답변하세요:

1. **뉴스 센티멘트 요약** (긍정/부정/중립 및 이유)
2. **주요 뉴스가 가격에 미친 영향** (상관관계 설명)
3. **핵심 상승/하락 요인** (구체적인 뉴스 제목 인용)
4. **단기 가격 전망** (24시간~7일, 근거 포함)
5. **투자자 주의사항** (리스크 요인)

분석은 사실에 근거하고, 추측은 명확히 구분하여 작성하세요.
투자 권유가 아닌 정보 제공 목적임을 명시하세요."""


def build_summary_prompt(news_list: list[dict], analysis_date: str) -> str:
    """일일 크립토 뉴스 전체 요약 프롬프트를 생성한다.

    매개변수:
        news_list: 뉴스 딕셔너리 목록
        analysis_date: 분석 날짜 문자열

    반환값:
        str: Groq API에 전달할 프롬프트 문자열
    """
    news_section = _format_news_section(news_list)

    return f"""{analysis_date} 크립토 시장 주요 뉴스를 한국어로 요약하세요.

## 뉴스 목록 ({len(news_list)}건)
{news_section}

## 요약 형식
- **오늘의 헤드라인**: 가장 중요한 뉴스 3건 한줄 요약
- **시장 전반 분위기**: 긍정/부정/혼조 및 이유
- **BTC 관련 주요 이슈**
- **ETH 관련 주요 이슈**
- **규제/매크로 이슈** (있는 경우)
- **총평**: 2-3문장 종합 의견

간결하고 명확하게 작성하세요."""


def _format_news_section(news_list: list[dict]) -> str:
    """뉴스 목록을 프롬프트용 텍스트로 포맷한다.

    매개변수:
        news_list: 뉴스 딕셔너리 목록

    반환값:
        str: 포맷된 뉴스 섹션 문자열
    """
    if not news_list:
        return "수집된 뉴스가 없습니다."

    lines = []
    for i, news in enumerate(news_list[:20], 1):
        title = news.get("title", "")
        source = news.get("source", "")
        body_preview = (news.get("body", "") or "")[:200]
        lines.append(f"{i}. [{source}] {title}\n   {body_preview}...")

    return "\n\n".join(lines)


def _format_price_section(coin: str, price_data: dict) -> str:
    """가격 데이터를 프롬프트용 텍스트로 포맷한다.

    매개변수:
        coin: 코인 심볼
        price_data: 가격 딕셔너리

    반환값:
        str: 포맷된 가격 섹션 문자열
    """
    if not price_data:
        return f"{coin}: 가격 데이터 없음"

    price = price_data.get("price_usd", 0)
    change_24h = price_data.get("change_24h", 0) or 0
    change_7d = price_data.get("change_7d", 0) or 0
    market_cap = price_data.get("market_cap", 0) or 0
    volume = price_data.get("volume_24h", 0) or 0

    direction_24h = "▲" if change_24h >= 0 else "▼"
    direction_7d = "▲" if change_7d >= 0 else "▼"

    return (
        f"- 현재가: ${price:,.2f}\n"
        f"- 24시간 변동: {direction_24h} {abs(change_24h):.2f}%\n"
        f"- 7일 변동: {direction_7d} {abs(change_7d):.2f}%\n"
        f"- 시가총액: ${market_cap:,.0f}\n"
        f"- 24시간 거래량: ${volume:,.0f}"
    )
