import datetime as dt
import logging
import os
import sys
from dataclasses import dataclass
from zoneinfo import ZoneInfo

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
EVENT_NAME = os.getenv("GITHUB_EVENT_NAME", "manual")
KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class Config:
    min_prev_volume_ratio: float = 1.8
    min_prev_change_pct: float = 2.0
    min_prev_close_position: float = 0.7
    min_open_gap_pct: float = -4.0
    max_open_gap_pct: float = 1.0
    min_rebound_from_open_pct: float = 0.8
    min_today_volume_vs_prev_pct: float = 3.0
    min_score: int = 6
    top_n: int = 12


CONFIG = Config()


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


def now_kst() -> dt.datetime:
    return dt.datetime.now(KST)


def send_telegram(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID가 없습니다. 텔레그램 전송 없이 화면에만 출력합니다.")
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


def get_ticker_frame(data: pd.DataFrame, ticker: str) -> pd.DataFrame | None:
    if data is None or data.empty:
        return None
    if isinstance(data.columns, pd.MultiIndex):
        if ticker not in data.columns.get_level_values(0):
            return None
        frame = data[ticker].dropna()
    else:
        frame = data.dropna()

    required = {"Open", "High", "Low", "Close", "Volume"}
    if frame.empty or not required.issubset(set(frame.columns)):
        return None
    return frame


def get_previous_session(daily: pd.DataFrame, today: dt.date) -> tuple[pd.Series, pd.Series] | None:
    daily = daily.dropna().copy()
    if daily.empty or len(daily) < 25:
        return None
    dates = pd.to_datetime(daily.index).date
    before_today = daily[dates < today]
    if len(before_today) < 25:
        before_today = daily.iloc[:-1]
    if len(before_today) < 25:
        return None
    return before_today.iloc[-1], before_today.iloc[-2]


def today_minutes(intraday: pd.DataFrame, today: dt.date) -> pd.DataFrame:
    if intraday.empty:
        return intraday
    index = pd.to_datetime(intraday.index)
    if index.tz is None:
        index = index.tz_localize("UTC").tz_convert(KST)
    else:
        index = index.tz_convert(KST)
    df = intraday.copy()
    df.index = index
    return df[index.date == today].dropna()


def pct(a: float, b: float) -> float:
    return ((a - b) / b) * 100 if b else 0.0


def analyze_one(
    ticker: str,
    name: str,
    daily: pd.DataFrame,
    intraday: pd.DataFrame,
    today: dt.date,
) -> dict | None:
    previous = get_previous_session(daily, today)
    if not previous:
        return None

    prev_day, prev_prev_day = previous
    day_minutes = today_minutes(intraday, today)
    if day_minutes.empty:
        return None

    prev_close = float(prev_day["Close"])
    prev_high = float(prev_day["High"])
    prev_low = float(prev_day["Low"])
    prev_volume = float(prev_day["Volume"])
    prev_change_pct = pct(prev_close, float(prev_prev_day["Close"]))

    daily_before_today = daily[pd.to_datetime(daily.index).date < today]
    vol20 = float(daily_before_today["Volume"].tail(20).mean())
    ma20 = float(daily_before_today["Close"].tail(20).mean())
    ma60 = float(daily_before_today["Close"].tail(60).mean())

    open_price = float(day_minutes["Open"].iloc[0])
    last_price = float(day_minutes["Close"].iloc[-1])
    high_price = float(day_minutes["High"].max())
    today_volume = float(day_minutes["Volume"].sum())

    open_gap_pct = pct(open_price, prev_close)
    rebound_from_open_pct = pct(last_price, open_price)
    current_change_pct = pct(last_price, prev_close)
    today_volume_vs_prev_pct = today_volume / max(prev_volume, 1) * 100
    prev_volume_ratio = prev_volume / max(vol20, 1)
    prev_close_position = (prev_close - prev_low) / max(prev_high - prev_low, 1)
    near_today_high = last_price >= high_price * 0.985

    checks = {
        "prev_volume_spike": prev_volume_ratio >= CONFIG.min_prev_volume_ratio,
        "prev_strong_up": prev_change_pct >= CONFIG.min_prev_change_pct,
        "prev_close_near_high": prev_close_position >= CONFIG.min_prev_close_position,
        "above_ma20": prev_close >= ma20,
        "above_ma60": prev_close >= ma60,
        "morning_gap_ok": CONFIG.min_open_gap_pct <= open_gap_pct <= CONFIG.max_open_gap_pct,
        "rebound_from_open": rebound_from_open_pct >= CONFIG.min_rebound_from_open_pct,
        "morning_volume_ok": today_volume_vs_prev_pct >= CONFIG.min_today_volume_vs_prev_pct,
        "near_today_high": near_today_high,
    }

    required = checks["morning_gap_ok"] and checks["rebound_from_open"]
    score = sum(checks.values())
    if not required or score < CONFIG.min_score:
        return None

    return {
        "ticker": ticker,
        "name": name,
        "score": score,
        "prev_change_pct": prev_change_pct,
        "prev_volume_ratio": prev_volume_ratio,
        "prev_close_position": prev_close_position,
        "open_gap_pct": open_gap_pct,
        "rebound_from_open_pct": rebound_from_open_pct,
        "current_change_pct": current_change_pct,
        "today_volume_vs_prev_pct": today_volume_vs_prev_pct,
        "last_price": last_price,
        "near_today_high": near_today_high,
        "checks": checks,
    }


def format_signal(item: dict) -> str:
    near_high = "예" if item["near_today_high"] else "아니오"
    return (
        f"<b>{item['name']} ({item['ticker']})</b>\n"
        f"점수: <b>{item['score']}/9</b>\n"
        f"현재가: {item['last_price']:,.0f}원 (전일 종가 대비 {item['current_change_pct']:+.2f}%)\n"
        f"시초가 갭: {item['open_gap_pct']:+.2f}% / 시초가 대비 반등: {item['rebound_from_open_pct']:+.2f}%\n"
        f"전일 등락률: {item['prev_change_pct']:+.2f}% / 전일 거래량: 20일 평균의 {item['prev_volume_ratio']:.1f}배\n"
        f"금일 누적 거래량: 전일의 {item['today_volume_vs_prev_pct']:.1f}% / 당일 고가 근처: {near_high}"
    )


def scan() -> list[dict]:
    tickers = list(TICKERS)
    today = now_kst().date()

    daily_all = yf.download(
        tickers,
        period="4mo",
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False,
    )
    intraday_all = yf.download(
        tickers,
        period="5d",
        interval="1m",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False,
    )

    results = []
    for ticker, name in TICKERS.items():
        try:
            daily = get_ticker_frame(daily_all, ticker)
            intraday = get_ticker_frame(intraday_all, ticker)
            if daily is None or intraday is None:
                print(f"{ticker} 건너뜀: 일봉 또는 분봉 데이터가 비어 있습니다.")
                continue
            item = analyze_one(ticker, name, daily, intraday, today)
            if item:
                results.append(item)
        except Exception as exc:
            print(f"{ticker} 처리 실패: {exc}")

    return sorted(
        results,
        key=lambda x: (
            x["score"],
            x["rebound_from_open_pct"],
            x["today_volume_vs_prev_pct"],
        ),
        reverse=True,
    )[: CONFIG.top_n]


def main() -> int:
    current = now_kst()
    current_text = current.strftime("%Y-%m-%d %H:%M")
    print(f"[{current_text}] 오전 반등 검색기를 시작합니다. event={EVENT_NAME}")

    if EVENT_NAME == "schedule" and current.hour >= 16:
        print("장이 마감되었습니다. 예약 실행을 건너뜁니다.")
        return 0

    results = scan()
    if not results:
        send_telegram(
            f"<b>[{current_text}] 오전 반등 검색기</b>\n\n"
            "조건에 맞는 후보가 없습니다.\n"
            "임시 yfinance 버전입니다. 권장 실행 시간: 한국시간 09:30-09:45."
        )
        return 0

    header = (
        f"<b>[{current_text}] 오전 반등 후보</b>\n"
        f"발견 종목 수: <b>{len(results)}</b>\n"
        "조건: 전일 거래량 급증 + 오전 갭 조건 + 시초가 대비 반등\n"
    )
    messages = []
    for i in range(0, len(results), 4):
        body = "\n\n".join(format_signal(item) for item in results[i : i + 4])
        messages.append((header + "\n" if i == 0 else "") + body)

    for message in messages:
        send_telegram(message)

    print(f"후보 {len(results)}개를 전송했습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
