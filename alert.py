import datetime as dt
import os
import sys
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import yfinance as yf


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")
EVENT_NAME = os.getenv("GITHUB_EVENT_NAME", "manual")
KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class ScanConfig:
    min_change_pct: float = 2.0
    max_change_pct: float = 5.0
    min_volume_ratio: float = 1.5
    near_high_pct: float = 1.5
    breakout_lookback: int = 60
    min_score: int = 6


CONFIG = ScanConfig()


TICKERS = {
    # KOSPI large caps
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
    "018260.KS": "삼성에스디에스",
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
    # KOSDAQ leaders
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
    "041510.KQ": "에스엠",
    "122870.KQ": "와이지엔터테인먼트",
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


def analyze(ticker: str, name: str, df: pd.DataFrame) -> dict | None:
    df = df.dropna().copy()
    if len(df) < 80:
        return None

    close = df["Close"]
    volume = df["Volume"]
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

    checks = {
        "RSI 45~70": 45 <= as_float(latest["rsi"]) <= 70,
        "MACD 상승": as_float(latest["macd"]) > as_float(latest["macd_signal"])
        and as_float(latest["macd_hist"]) > as_float(previous["macd_hist"]),
        "거래량 증가": volume_ratio >= CONFIG.min_volume_ratio,
        "20일선 위": price > as_float(latest["ma20"]),
        "60일선 위": price > as_float(latest["ma60"]),
        "당일 +2% 이상": CONFIG.min_change_pct <= change_pct <= CONFIG.max_change_pct,
        "전고점 돌파 시도": price >= high_lookback or distance_to_high_pct <= CONFIG.near_high_pct,
    }
    score = sum(checks.values())

    if score < CONFIG.min_score:
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
        "checks": checks,
    }


def format_signal(signal: dict) -> str:
    passed = " / ".join(name for name, ok in signal["checks"].items() if ok)
    breakout = (
        "돌파"
        if signal["price"] >= signal["high_lookback"]
        else f"전고점까지 {signal['distance_to_high_pct']:.2f}%"
    )
    return (
        f"<b>{signal['name']} ({signal['ticker']})</b>\n"
        f"점수: <b>{signal['score']}/7</b>\n"
        f"현재가: {signal['price']:,.0f}원 ({signal['change_pct']:+.2f}%)\n"
        f"RSI: {signal['rsi']:.1f} / 거래량: 20일 평균의 {signal['volume_ratio']:.1f}배\n"
        f"전고점: {signal['high_lookback']:,.0f}원 ({breakout})\n"
        f"통과: {passed}"
    )


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
                continue
            signal = analyze(ticker, name, data[ticker])
            if signal:
                signals.append(signal)
        except Exception as exc:
            print(f"{ticker} 분석 실패: {exc}")

    return sorted(
        signals,
        key=lambda x: (x["score"], x["change_pct"], x["volume_ratio"]),
        reverse=True,
    )


def main() -> int:
    current = now_kst()
    current_text = current.strftime("%Y-%m-%d %H:%M")
    if should_stop_for_schedule(current):
        print(f"[{current_text}] 장 마감 이후 예약 실행이라 종료합니다.")
        return 0

    print(f"[{current_text}] 국장 스캐너를 시작합니다. event={EVENT_NAME}")
    signals = scan()

    if not signals:
        send_telegram(
            f"📊 <b>[{current_text}] 국장 스캐너 완료</b>\n\n"
            "조건을 만족한 종목이 없습니다.\n"
            "조건: RSI + MACD + 거래량 + 20/60일선 + 상승률 + 전고점"
        )
        return 0

    header = (
        f"📈 <b>[{current_text}] 국장 단타 스캐너</b>\n"
        f"조건 통과: <b>{len(signals)}개</b>\n"
        "기준: 7개 조건 중 6개 이상 통과\n"
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
