import datetime as dt
import html
import logging
import os
import re
import sys
import zipfile
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from io import BytesIO
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import yfinance as yf


logging.getLogger("yfinance").setLevel(logging.CRITICAL)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")
DART_API_KEY = os.getenv("DART_API_KEY") or os.getenv("OPENDART_API_KEY")
KRX_API_KEY = os.getenv("KRX_API_KEY")
EVENT_NAME = os.getenv("GITHUB_EVENT_NAME", "manual")
KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class ScanConfig:
    min_change_pct: float = 1.0
    max_change_pct: float = 10.0
    min_volume_ratio: float = 1.2
    near_high_pct: float = 3.0
    breakout_lookback: int = 60
    max_long_bearish_body_pct: float = 5.0
    min_close_position: float = 0.7
    min_score: int = 6
    top_n: int = 20
    news_fetch_n: int = 12
    news_top_n: int = 3
    disclosure_top_n: int = 3
    supply_lookback_days: int = 14
    foreign_surge_ratio: float = 2.0
    min_foreign_net_buy_krw: int = 500_000_000
    min_institution_net_buy_krw: int = 300_000_000
    theme_top_n: int = 5
    technical_weight: float = 0.7
    material_weight: float = 0.3
    max_material_score: int = 6
    near_high_bonus_3pct: float = 2.0
    near_high_bonus_1pct: float = 3.0
    far_from_high_penalty_8pct: float = -2.0
    rsi_penalty_75: float = -5.0
    rsi_penalty_80: float = -10.0
    change_penalty_8pct: float = -5.0
    low_volume_penalty: float = -5.0


CONFIG = ScanConfig()


TICKERS = {
    "005930.KS": "삼성전자",
    "000660.KS": "SK하이닉스",
    "005380.KS": "현대차",
    "000270.KS": "기아",
    "035420.KS": "NAVER",
    "035720.KS": "카카오",
    "068270.KS": "셀트리온",
    "005490.KS": "POSCO홀딩스",
    "051910.KS": "LG화학",
    "006400.KS": "삼성SDI",
    "373220.KS": "LG에너지솔루션",
    "105560.KS": "KB금융",
    "055550.KS": "신한지주",
    "086790.KS": "하나금융지주",
    "316140.KS": "우리금융지주",
    "012330.KS": "현대모비스",
    "028260.KS": "삼성물산",
    "032830.KS": "삼성생명",
    "066570.KS": "LG전자",
    "003550.KS": "LG",
    "034730.KS": "SK",
    "096770.KS": "SK이노베이션",
    "015760.KS": "한국전력",
    "033780.KS": "KT&G",
    "017670.KS": "SK텔레콤",
    "030200.KS": "KT",
    "009150.KS": "삼성전기",
    "010130.KS": "고려아연",
    "010950.KS": "S-Oil",
    "011200.KS": "HMM",
    "047050.KS": "포스코인터내셔널",
    "042660.KS": "한화오션",
    "009540.KS": "HD한국조선해양",
    "329180.KS": "HD현대중공업",
    "010140.KS": "삼성중공업",
    "034020.KS": "두산에너빌리티",
    "012450.KS": "한화에어로스페이스",
    "000720.KS": "현대건설",
    "028050.KS": "삼성E&A",
    "051900.KS": "LG생활건강",
    "090430.KS": "아모레퍼시픽",
    "097950.KS": "CJ제일제당",
    "018260.KS": "삼성SDS",
    "036570.KS": "엔씨소프트",
    "259960.KS": "크래프톤",
    "302440.KS": "SK바이오사이언스",
    "326030.KS": "SK바이오팜",
    "128940.KS": "한미약품",
    "011070.KS": "LG이노텍",
    "034220.KS": "LG디스플레이",
    "004020.KS": "현대제철",
    "006260.KS": "LS",
    "010120.KS": "LS ELECTRIC",
    "071050.KS": "한국금융지주",
    "016360.KS": "삼성증권",
    "024110.KS": "기업은행",
    "000810.KS": "삼성화재",
    "005830.KS": "DB손해보험",
    "138040.KS": "메리츠금융지주",
    "247540.KQ": "에코프로비엠",
    "086520.KQ": "에코프로",
    "066970.KQ": "엘앤에프",
    "028300.KQ": "HLB",
    "196170.KQ": "알테오젠",
    "068760.KQ": "셀트리온제약",
    "145020.KQ": "휴젤",
    "214150.KQ": "클래시스",
    "058470.KQ": "리노공업",
    "112040.KQ": "위메이드",
    "035900.KQ": "JYP Ent.",
    "041510.KQ": "SM",
    "122870.KQ": "YG Ent.",
    "293490.KQ": "카카오게임즈",
    "263750.KQ": "펄어비스",
    "067160.KQ": "메디톡스",
    "086900.KQ": "메디톡스",
    "039030.KQ": "이오테크닉스",
    "036830.KQ": "솔브레인",
    "095340.KQ": "ISC",
    "240810.KQ": "원익IPS",
    "078340.KQ": "컴투스",
    "060250.KQ": "NHN KCP",
    "035600.KQ": "KG이니시스",
    "000250.KQ": "삼천당제약",
    "084370.KQ": "유진테크",
    "098460.KQ": "고영",
    "053030.KQ": "바이넥스",
    "042000.KQ": "카페24",
}


THEMES = {
    "AI 반도체": [
        "ai",
        "hbm",
        "hbm4",
        "hbm4e",
        "반도체",
        "gpu",
        "엔비디아",
        "데이터센터",
        "메모리",
        "파운드리",
    ],
    "보험업 재평가": [
        "보험",
        "손보",
        "생보",
        "보험계약",
        "보험계약대출",
        "생명보험",
        "손해보험",
        "ifrs17",
        "킥스",
        "투자손익",
    ],
    "게임": [
        "게임",
        "신작",
        "흥행",
        "리니지",
        "글로벌",
        "출시",
        "턴어라운드",
    ],
    "스테이블코인/결제": [
        "스테이블코인",
        "결제",
        "pg",
        "가상자산",
        "원화",
        "거래액",
        "핀테크",
    ],
    "조선/방산": [
        "조선",
        "선박",
        "수주",
        "방산",
        "항공우주",
        "잠수함",
        "함정",
    ],
    "건설/재건축": [
        "건설",
        "재건축",
        "재개발",
        "수주",
        "반포",
        "압구정",
    ],
    "바이오": [
        "바이오",
        "임상",
        "fda",
        "신약",
        "품목허가",
        "기술이전",
    ],
    "2차전지": [
        "2차전지",
        "배터리",
        "양극재",
        "전기차",
        "리튬",
        "에코프로",
    ],
}


STATIC_THEMES = {
    "삼성전자": ["AI 반도체"],
    "SK하이닉스": ["AI 반도체"],
    "삼성생명": ["보험업 재평가"],
    "삼성화재": ["보험업 재평가"],
    "DB손해보험": ["보험업 재평가"],
    "엔씨소프트": ["게임"],
    "크래프톤": ["게임"],
    "위메이드": ["게임"],
    "NHN KCP": ["스테이블코인/결제"],
    "KG이니시스": ["스테이블코인/결제"],
    "삼성물산": ["건설/재건축"],
    "현대건설": ["건설/재건축"],
    "HD한국조선해양": ["조선/방산"],
    "HD현대중공업": ["조선/방산"],
    "한화오션": ["조선/방산"],
    "한화에어로스페이스": ["조선/방산"],
}


THEME_ELIGIBLE_NAMES = {
    theme: {name for name, themes in STATIC_THEMES.items() if theme in themes}
    for theme in THEMES
}


STRONG_NEWS_KEYWORDS = {
    "자사주": 5,
    "공급": 5,
    "수주": 5,
    "계약": 5,
    "인수": 5,
    "합병": 5,
    "실적 서프라이즈": 5,
    "흑자전환": 5,
    "신고가": 4,
    "목표가": 4,
    "상향": 4,
    "배당": 4,
    "주주환원": 4,
    "승인": 4,
    "허가": 4,
    "출시": 3,
    "흥행": 3,
    "기대": 2,
}


GOOD_NEWS_KEYWORDS = {
    "목표가": 2,
    "상향": 2,
    "신규 커버리지": 2,
    "실적 상향": 2,
    "수주": 2,
    "공급계약": 2,
    "계약 체결": 2,
    "m&a": 2,
    "인수": 2,
    "합병": 2,
    "자사주": 2,
    "배당": 2,
    "주주환원": 2,
    "흑자전환": 2,
    "실적 서프라이즈": 2,
    "어닝 서프라이즈": 2,
}


DROP_NEWS_KEYWORDS = [
    "주가 상승 중",
    "주가 강세",
    "상승세",
    "장중 수급 포착",
    "장중",
    "시황",
    "마감 시황",
    "증시",
    "코스피",
    "코스닥",
    "특징주",
    "오늘의 종목",
    "투자분석",
]


def now_kst() -> dt.datetime:
    return dt.datetime.now(KST)


def should_stop_for_schedule(now: dt.datetime) -> bool:
    return EVENT_NAME == "schedule" and now.hour >= 16


def send_telegram(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID가 없어 텔레그램 전송을 건너뜁니다.")
        print(text)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    response.raise_for_status()


def stock_code(ticker: str) -> str:
    return ticker.split(".", 1)[0]


def request_json(url: str, params: dict, timeout: int = 10) -> dict | None:
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        print(f"외부 데이터 요청 실패: {exc}")
        return None


def clean_news_title(title: str) -> str:
    title = html.unescape(title).strip()
    if " - " in title:
        title = title.rsplit(" - ", 1)[0]
    return re.sub(r"\s+", " ", title)


def normalize_news_title(title: str) -> str:
    title = clean_news_title(title).lower()
    title = re.sub(r"[^0-9a-z가-힣]+", " ", title)
    stopwords = {"단독", "종합", "특징주", "속보", "포토", "영상"}
    tokens = [token for token in title.split() if token not in stopwords and len(token) > 1]
    return " ".join(tokens)


def token_set(text: str) -> set[str]:
    return set(normalize_news_title(text).split())


def similar_news(a: str, b: str) -> bool:
    left = token_set(a)
    right = token_set(b)
    if not left or not right:
        return False
    return len(left & right) / max(len(left | right), 1) >= 0.45


def is_low_quality_news(title: str) -> bool:
    lowered = title.lower()
    return any(keyword.lower() in lowered for keyword in DROP_NEWS_KEYWORDS)


def news_quality_bonus(title: str) -> int:
    lowered = title.lower()
    return max(
        (bonus for keyword, bonus in GOOD_NEWS_KEYWORDS.items() if keyword.lower() in lowered),
        default=0,
    )


def news_published_at(item: ET.Element) -> dt.datetime | None:
    pub_date = item.findtext("pubDate", default="").strip()
    if not pub_date:
        return None
    try:
        parsed = parsedate_to_datetime(pub_date)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(KST)


def age_text(published_at: dt.datetime | None) -> str:
    if not published_at:
        return "시간 미상"
    minutes = max(int((now_kst() - published_at).total_seconds() // 60), 0)
    if minutes < 60:
        return f"{minutes}분 전"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}시간 전"
    return f"{hours // 24}일 전"


def detect_themes(text: str, name: str = "") -> list[str]:
    haystack = f"{name} {text}".lower()
    themes = set()
    for theme, keywords in THEMES.items():
        eligible_names = THEME_ELIGIBLE_NAMES.get(theme, set())
        if eligible_names and name not in eligible_names:
            continue
        if any(keyword.lower() in haystack for keyword in keywords):
            themes.add(theme)
    return sorted(themes)


def news_strength(title: str, published_at: dt.datetime | None, duplicate_count: int = 1) -> int:
    if is_low_quality_news(title):
        return 0

    lowered = title.lower()
    score = 1 + news_quality_bonus(title)
    for keyword, value in STRONG_NEWS_KEYWORDS.items():
        if keyword.lower() in lowered:
            score = max(score, value)

    if published_at:
        hours = (now_kst() - published_at).total_seconds() / 3600
        if hours <= 2:
            score += 1
        elif hours > 48:
            score -= 1

    if duplicate_count >= 3:
        score += 1
    return max(1, min(score, 5))


def stars(score: int) -> str:
    return "★" * score + "☆" * (5 - score)


def fetch_news_summary(name: str) -> dict:
    query = f"{name} 주가 OR 실적 OR 수주 OR 계약 OR 투자"
    try:
        response = requests.get(
            "https://news.google.com/rss/search",
            params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"},
            timeout=10,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except Exception as exc:
        print(f"{name} 뉴스 조회 실패: {exc}")
        return {"items": [], "recent_3d_count": 0, "themes": [], "max_strength": 0}

    raw_items = []
    for item in root.findall("./channel/item"):
        title = item.findtext("title", default="").strip()
        if title:
            clean_title = clean_news_title(title)
            if is_low_quality_news(clean_title):
                continue
            published_at = news_published_at(item)
            raw_items.append(
                {
                    "title": clean_title,
                    "published_at": published_at,
                    "themes": detect_themes(clean_title, name),
                }
            )
        if len(raw_items) >= CONFIG.news_fetch_n:
            break

    recent_3d_count = 0
    cutoff = now_kst() - dt.timedelta(days=3)
    for item in raw_items:
        if item["published_at"] and item["published_at"] >= cutoff:
            recent_3d_count += 1

    groups: list[dict] = []
    for item in raw_items:
        matched = None
        for group in groups:
            if similar_news(item["title"], group["title"]):
                matched = group
                break
        if matched:
            matched["duplicate_count"] += 1
            matched["themes"] = sorted(set(matched["themes"]) | set(item["themes"]))
            if item["published_at"] and (
                not matched["published_at"] or item["published_at"] > matched["published_at"]
            ):
                matched["title"] = item["title"]
                matched["published_at"] = item["published_at"]
        else:
            groups.append({**item, "duplicate_count": 1})

    for group in groups:
        group["strength"] = news_strength(
            group["title"],
            group["published_at"],
            group["duplicate_count"],
        )
        if group["strength"] <= 0:
            continue
        group["age"] = age_text(group["published_at"])
        group["stars"] = stars(group["strength"])

    groups = [group for group in groups if group.get("strength", 0) > 0]
    groups = sorted(
        groups,
        key=lambda x: (
            x["strength"],
            x["published_at"] or dt.datetime.min.replace(tzinfo=KST),
            x["duplicate_count"],
        ),
        reverse=True,
    )
    themes = sorted({theme for group in groups for theme in group["themes"]})
    max_strength = max((group["strength"] for group in groups), default=0)
    return {
        "items": groups[: CONFIG.news_top_n],
        "recent_3d_count": recent_3d_count,
        "themes": themes,
        "max_strength": max_strength,
    }


_DART_CORP_CODES: dict[str, str] | None = None


def load_dart_corp_codes() -> dict[str, str]:
    global _DART_CORP_CODES
    if _DART_CORP_CODES is not None:
        return _DART_CORP_CODES

    mapping: dict[str, str] = {}
    manual_mapping = os.getenv("DART_CORP_CODES", "")
    for pair in manual_mapping.split(","):
        if "=" in pair:
            code, corp_code = pair.split("=", 1)
            mapping[code.strip()] = corp_code.strip()

    if not DART_API_KEY:
        _DART_CORP_CODES = mapping
        return _DART_CORP_CODES

    try:
        response = requests.get(
            "https://opendart.fss.or.kr/api/corpCode.xml",
            params={"crtfc_key": DART_API_KEY},
            timeout=20,
        )
        response.raise_for_status()
        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            xml_bytes = archive.read("CORPCODE.xml")
        root = ET.fromstring(xml_bytes)
        for item in root.findall("list"):
            code = item.findtext("stock_code", default="").strip()
            corp_code = item.findtext("corp_code", default="").strip()
            if code and corp_code:
                mapping[code] = corp_code
    except Exception as exc:
        print(f"DART 기업코드 조회 실패: {exc}")

    _DART_CORP_CODES = mapping
    return _DART_CORP_CODES


def fetch_disclosure_summary(ticker: str) -> list[str]:
    if not DART_API_KEY:
        return []

    corp_code = load_dart_corp_codes().get(stock_code(ticker))
    if not corp_code:
        return []

    today = now_kst().date()
    start = today - dt.timedelta(days=7)
    data = request_json(
        "https://opendart.fss.or.kr/api/list.json",
        {
            "crtfc_key": DART_API_KEY,
            "corp_code": corp_code,
            "bgn_de": start.strftime("%Y%m%d"),
            "end_de": today.strftime("%Y%m%d"),
            "page_count": CONFIG.disclosure_top_n,
            "sort": "date",
            "sort_mth": "desc",
        },
    )
    if not data or data.get("status") not in {"000", "013"}:
        return []

    disclosures = []
    for item in data.get("list", []):
        date_text = item.get("rcept_dt", "")
        report = item.get("report_nm", "")
        if date_text and report:
            disclosures.append(f"{date_text} {report}")
    return disclosures[: CONFIG.disclosure_top_n]


def fetch_supply_summary(ticker: str) -> dict:
    if KRX_API_KEY:
        krx_url = os.getenv("KRX_SUPPLY_URL")
        if krx_url:
            print("KRX_SUPPLY_URL 방식은 서비스별 입력값이 달라 현재 pykrx 수급 조회를 우선 사용합니다.")

    try:
        from pykrx import stock
    except Exception:
        return {"available": False, "reason": "pykrx 미설치", "checks": {}, "lines": []}

    end = now_kst().date()
    start = end - dt.timedelta(days=CONFIG.supply_lookback_days)
    try:
        df = stock.get_market_trading_value_by_date(
            start.strftime("%Y%m%d"),
            end.strftime("%Y%m%d"),
            stock_code(ticker),
        )
    except Exception as exc:
        return {"available": False, "reason": f"수급 조회 실패: {exc}", "checks": {}, "lines": []}

    if df is None or df.empty:
        return {"available": False, "reason": "수급 데이터 없음", "checks": {}, "lines": []}

    foreign_col = "외국인합계" if "외국인합계" in df.columns else "외국인"
    institution_col = "기관합계"
    if foreign_col not in df.columns or institution_col not in df.columns:
        return {"available": False, "reason": "외국인/기관 컬럼 없음", "checks": {}, "lines": []}

    df = df[[foreign_col, institution_col]].dropna()
    if len(df) < 2:
        return {"available": False, "reason": "수급 데이터 부족", "checks": {}, "lines": []}

    latest = df.iloc[-1]
    previous = df.iloc[-2]
    foreign_net = float(latest[foreign_col])
    institution_net = float(latest[institution_col])
    prev_institution_net = float(previous[institution_col])
    foreign_avg = float(df[foreign_col].iloc[:-1].tail(5).mean())
    foreign_base = max(abs(foreign_avg), 1)

    checks = {
        "외국인 순매수": foreign_net >= CONFIG.min_foreign_net_buy_krw,
        "외국인 순매수 급증": foreign_net > 0 and foreign_net / foreign_base >= CONFIG.foreign_surge_ratio,
        "기관 순매수 전환": institution_net >= CONFIG.min_institution_net_buy_krw and prev_institution_net <= 0,
        "외국인+기관 동시 순매수": foreign_net > 0 and institution_net > 0,
    }
    lines = [
        f"외국인 {foreign_net / 100_000_000:+.1f}억원",
        f"기관 {institution_net / 100_000_000:+.1f}억원",
    ]
    passed = [name for name, ok in checks.items() if ok]
    if passed:
        lines.append("통과: " + ", ".join(passed))

    return {"available": True, "reason": "", "checks": checks, "lines": lines}


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    fast = close.ewm(span=12, adjust=False).mean()
    slow = close.ewm(span=26, adjust=False).mean()
    line = fast - slow
    signal = line.ewm(span=9, adjust=False).mean()
    hist = line - signal
    return line, signal, hist


def as_float(value) -> float:
    return float(value.item() if hasattr(value, "item") else value)


def has_price_data(df: pd.DataFrame | None, min_rows: int = 80) -> bool:
    if df is None or df.empty or len(df.dropna()) < min_rows:
        return False
    required = {"Open", "High", "Low", "Close", "Volume"}
    return required.issubset(set(df.columns))


def analyze(ticker: str, name: str, df: pd.DataFrame) -> dict | None:
    df = df.dropna().copy()
    if len(df) < 80:
        return None

    close = df["Close"]
    volume = df["Volume"]
    df["ma5"] = close.rolling(5).mean()
    df["ma20"] = close.rolling(20).mean()
    df["ma60"] = close.rolling(60).mean()
    df["rsi"] = rsi(close)
    df["macd"], df["macd_signal"], df["macd_hist"] = macd(close)
    df["vol20"] = volume.rolling(20).mean()

    latest = df.iloc[-1]
    previous = df.iloc[-2]
    recent_before_today = df.iloc[-CONFIG.breakout_lookback - 1 : -1]

    price = as_float(latest["Close"])
    prev_close = as_float(previous["Close"])
    change_pct = ((price - prev_close) / prev_close) * 100
    volume_ratio = as_float(latest["Volume"]) / max(as_float(latest["vol20"]), 1)
    high_lookback = as_float(recent_before_today["High"].max())
    distance_to_high_pct = ((high_lookback - price) / high_lookback) * 100
    day_range = max(as_float(latest["High"]) - as_float(latest["Low"]), 1)
    close_position = (price - as_float(latest["Low"])) / day_range
    ma5_above_ma20 = as_float(latest["ma5"]) > as_float(latest["ma20"])
    ma5_crossed_up_ma20 = as_float(previous["ma5"]) <= as_float(previous["ma20"]) and ma5_above_ma20

    has_long_bearish = False
    for _, candle in df.tail(3).iterrows():
        candle_open = as_float(candle["Open"])
        candle_close = as_float(candle["Close"])
        if candle_close < candle_open:
            body_pct = ((candle_open - candle_close) / candle_open) * 100
            if body_pct >= CONFIG.max_long_bearish_body_pct:
                has_long_bearish = True
                break

    checks = {
        "RSI 45~70": 45 <= as_float(latest["rsi"]) <= 70,
        "MACD 상승": as_float(latest["macd"]) > as_float(latest["macd_signal"])
        and as_float(latest["macd_hist"]) > as_float(previous["macd_hist"]),
        "거래량 증가": volume_ratio >= CONFIG.min_volume_ratio,
        "20일선 위": price > as_float(latest["ma20"]),
        "60일선 위": price > as_float(latest["ma60"]),
        "당일 상승률 범위": CONFIG.min_change_pct <= change_pct <= CONFIG.max_change_pct,
        "전고점 돌파 시도": price >= high_lookback or distance_to_high_pct <= CONFIG.near_high_pct,
        "종가 고가권": close_position >= CONFIG.min_close_position,
        "5일선 20일선 돌파": ma5_above_ma20 or ma5_crossed_up_ma20,
    }
    score = sum(checks.values())

    if has_long_bearish or not checks["당일 상승률 범위"] or score < CONFIG.min_score:
        return None

    return {
        "ticker": ticker,
        "name": name,
        "score": score,
        "price": price,
        "change_pct": change_pct,
        "rsi": as_float(latest["rsi"]),
        "volume_ratio": volume_ratio,
        "high_lookback": high_lookback,
        "distance_to_high_pct": distance_to_high_pct,
        "close_position": close_position,
        "ma5": as_float(latest["ma5"]),
        "ma20": as_float(latest["ma20"]),
        "checks": checks,
    }


def enrich_signal(signal: dict) -> dict:
    signal = signal.copy()
    news = fetch_news_summary(signal["name"])
    disclosures = fetch_disclosure_summary(signal["ticker"])
    supply = fetch_supply_summary(signal["ticker"])

    extra_score = 0
    news_strength_score = news.get("max_strength", 0)
    if news_strength_score:
        extra_score += max(1, min(3, news_strength_score - 2))
    if disclosures:
        extra_score += 1
    extra_score += sum(supply.get("checks", {}).values())

    themes = sorted(set(news.get("themes", [])) | set(STATIC_THEMES.get(signal["name"], [])))
    if themes:
        extra_score += 1

    signal["news"] = news
    signal["themes"] = themes
    signal["news_strength"] = news_strength_score
    signal["recent_3d_news_count"] = news.get("recent_3d_count", 0)
    signal["disclosures"] = disclosures
    signal["supply"] = supply
    signal["extra_score"] = extra_score
    material_score = min(extra_score, CONFIG.max_material_score)
    technical_ratio = signal["score"] / 9
    material_ratio = material_score / max(CONFIG.max_material_score, 1)
    base_weighted_score = (
        technical_ratio * CONFIG.technical_weight
        + material_ratio * CONFIG.material_weight
    ) * 100
    entry_adjustment, adjustment_reasons = entry_adjustments(signal)
    weighted_score = base_weighted_score + entry_adjustment
    signal["material_score"] = material_score
    signal["total_score"] = signal["score"] + extra_score
    signal["base_weighted_score"] = base_weighted_score
    signal["entry_adjustment"] = entry_adjustment
    signal["adjustment_reasons"] = adjustment_reasons
    signal["weighted_score"] = max(weighted_score, 0)
    return signal


def entry_adjustments(signal: dict) -> tuple[float, list[str]]:
    adjustment = 0.0
    reasons = []

    distance = signal["distance_to_high_pct"]
    if distance < 1:
        adjustment += CONFIG.near_high_bonus_1pct
        reasons.append(f"전고점 1% 이내 +{CONFIG.near_high_bonus_1pct:g}")
    elif distance < 3:
        adjustment += CONFIG.near_high_bonus_3pct
        reasons.append(f"전고점 3% 이내 +{CONFIG.near_high_bonus_3pct:g}")
    elif distance > 8:
        adjustment += CONFIG.far_from_high_penalty_8pct
        reasons.append(f"전고점 8% 초과 {CONFIG.far_from_high_penalty_8pct:g}")

    rsi_value = signal["rsi"]
    if rsi_value >= 80:
        adjustment += CONFIG.rsi_penalty_80
        reasons.append(f"RSI 80 이상 {CONFIG.rsi_penalty_80:g}")
    elif rsi_value >= 75:
        adjustment += CONFIG.rsi_penalty_75
        reasons.append(f"RSI 75 이상 {CONFIG.rsi_penalty_75:g}")

    if signal["change_pct"] >= 8:
        adjustment += CONFIG.change_penalty_8pct
        reasons.append(f"당일 상승률 8% 이상 {CONFIG.change_penalty_8pct:g}")

    if signal["volume_ratio"] < 0.8:
        adjustment += CONFIG.low_volume_penalty
        reasons.append(f"거래량 0.8배 미만 {CONFIG.low_volume_penalty:g}")

    return adjustment, reasons


def build_theme_summary(signals: list[dict]) -> list[dict]:
    theme_map: dict[str, dict] = {}
    for signal in signals:
        for theme in signal.get("themes", []):
            entry = theme_map.setdefault(
                theme,
                {
                    "theme": theme,
                    "names": [],
                    "recent_3d_count": 0,
                    "max_strength": 0,
                    "score": 0,
                },
            )
            if signal["name"] not in entry["names"]:
                entry["names"].append(signal["name"])
            entry["recent_3d_count"] += signal.get("recent_3d_news_count", 0)
            entry["max_strength"] = max(entry["max_strength"], signal.get("news_strength", 0))
            entry["score"] += signal.get("weighted_score", 0)

    summaries = []
    for entry in theme_map.values():
        related_count = len(entry["names"])
        theme_power = min(5, max(1, entry["max_strength"] + min(2, related_count - 1)))
        entry["theme_power"] = theme_power
        entry["stars"] = stars(theme_power)
        summaries.append(entry)

    return sorted(
        summaries,
        key=lambda x: (x["theme_power"], len(x["names"]), x["recent_3d_count"], x["score"]),
        reverse=True,
    )[: CONFIG.theme_top_n]


def format_theme_summary(theme_summary: list[dict]) -> str:
    if not theme_summary:
        return "오늘의 테마: 감지된 테마 없음"

    lines = ["오늘의 테마"]
    for item in theme_summary:
        names = ", ".join(item["names"][:6])
        if len(item["names"]) > 6:
            names += f" 외 {len(item['names']) - 6}개"
        lines.extend(
            [
                f"[{html.escape(item['theme'])}] {item['stars']}",
                f"최근 3일 뉴스 {item['recent_3d_count']}회 / 관련주: {html.escape(names)}",
            ]
        )
    return "\n".join(lines)


def format_signal(signal: dict) -> str:
    passed = " / ".join(name for name, ok in signal["checks"].items() if ok)
    total_checks = len(signal["checks"])
    breakout = (
        "돌파"
        if signal["price"] >= signal["high_lookback"]
        else f"전고점까지 {signal['distance_to_high_pct']:.2f}%"
    )

    lines = [
        f"<b>{signal['name']} ({signal['ticker']})</b>",
        f"순위점수: <b>{signal.get('weighted_score', 0):.1f}</b> "
        f"(기술 70% {signal['score']}/{total_checks} + 재료 30% {signal.get('material_score', 0)}/{CONFIG.max_material_score})",
        f"참고점수: 기술 {signal['score']}/{total_checks} + 재료/수급 {signal.get('extra_score', 0)}",
        f"진입보정: {signal.get('entry_adjustment', 0):+g}"
        + (
            " (" + ", ".join(html.escape(reason) for reason in signal.get("adjustment_reasons", [])) + ")"
            if signal.get("adjustment_reasons")
            else ""
        ),
        f"현재가: {signal['price']:,.0f}원 ({signal['change_pct']:+.2f}%)",
        f"RSI: {signal['rsi']:.1f} / 거래량: 20일 평균의 {signal['volume_ratio']:.1f}배",
        f"전고점: {signal['high_lookback']:,.0f}원 ({breakout})",
        f"종가 위치: 당일 저가~고가 중 {signal['close_position'] * 100:.0f}% 지점",
        f"MA5/MA20: {signal['ma5']:,.0f} / {signal['ma20']:,.0f}",
        f"통과: {html.escape(passed)}",
    ]

    supply = signal.get("supply") or {}
    if supply.get("available"):
        lines.append("수급: " + " / ".join(html.escape(line) for line in supply["lines"]))
    elif supply.get("reason"):
        lines.append(f"수급: {html.escape(supply['reason'])}")

    if signal.get("themes"):
        lines.append("테마: " + ", ".join(html.escape(theme) for theme in signal["themes"]))

    news = signal.get("news") or {}
    news_items = news.get("items", [])
    if news_items:
        lines.append(f"뉴스강도: {stars(signal.get('news_strength', 0))} / 최근 3일 {signal.get('recent_3d_news_count', 0)}회")
        news_lines = []
        for item in news_items:
            duplicate = f" 유사 {item['duplicate_count']}건" if item["duplicate_count"] > 1 else ""
            news_lines.append(
                f"{item['age']} {item['stars']} {html.escape(item['title'])}{duplicate}"
            )
        lines.append("뉴스: " + " | ".join(news_lines))

    if signal.get("disclosures"):
        lines.append("공시: " + " | ".join(html.escape(title) for title in signal["disclosures"]))

    return "\n".join(lines)


def scan() -> list[dict]:
    tickers = list(TICKERS)
    data = yf.download(
        tickers,
        period="6mo",
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False,
    )

    signals = []
    for ticker, name in TICKERS.items():
        try:
            if ticker not in data:
                print(f"{ticker} 건너뜀: 데이터 없음")
                continue
            ticker_data = data[ticker]
            if not has_price_data(ticker_data):
                print(f"{ticker} 건너뜀: 가격 데이터 부족")
                continue
            signal = analyze(ticker, name, ticker_data)
            if signal:
                signals.append(signal)
        except Exception as exc:
            print(f"{ticker} 분석 실패: {exc}")

    enriched = [enrich_signal(signal) for signal in signals]
    return sorted(
        enriched,
        key=lambda x: (
            x.get("weighted_score", 0),
            x["score"],
            x["change_pct"],
            x["volume_ratio"],
        ),
        reverse=True,
    )[: CONFIG.top_n]


def main() -> int:
    current = now_kst()
    current_text = current.strftime("%Y-%m-%d %H:%M")
    if should_stop_for_schedule(current):
        print(f"[{current_text}] 장 마감 이후 예약 실행이라 종료합니다.")
        return 0

    print(f"[{current_text}] 국장 스윙 알림을 시작합니다. event={EVENT_NAME}")
    signals = scan()

    if not signals:
        send_telegram(
            f"<b>[{current_text}] 국장 스윙 알림 완료</b>\n\n"
            "조건을 만족한 종목이 없습니다.\n"
            "조건: RSI + MACD + 거래량 + 20/60일선 + 상승률 + 전고점"
        )
        return 0

    header = (
        f"<b>[{current_text}] 국장 후보 알림</b>\n"
        f"조건 통과: <b>{len(signals)}개</b>\n"
        f"기준: 9개 기술 조건 중 {CONFIG.min_score}개 이상 통과, 정렬은 기술 70% + 재료/뉴스 30%\n"
        "참고: 공시는 DART_API_KEY, 수급은 pykrx/KRX_API_KEY 준비 상태에 따라 반영됩니다.\n"
        "\n"
        f"{format_theme_summary(build_theme_summary(signals))}\n"
    )
    chunks = [signals[i : i + 5] for i in range(0, len(signals), 5)]
    for index, chunk in enumerate(chunks, start=1):
        body = "\n\n".join(format_signal(signal) for signal in chunk)
        prefix = header + "\n" if index == 1 else ""
        send_telegram(prefix + body)

    print(f"총 {len(signals)}개 종목 전송 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
