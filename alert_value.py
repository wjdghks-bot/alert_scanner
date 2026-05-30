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
    "005930.KS": "SamsungElec",
    "000660.KS": "SKHynix",
    "005380.KS": "HyundaiMotor",
    "000270.KS": "Kia",
    "035420.KS": "NAVER",
    "035720.KS": "Kakao",
    "068270.KS": "Celltrion",
    "005490.KS": "POSCOHoldings",
    "051910.KS": "LGChem",
    "006400.KS": "SamsungSDI",
    "373220.KS": "LGEnergySolution",
    "105560.KS": "KBFinancial",
    "055550.KS": "Shinhan",
    "086790.KS": "HanaFinancial",
    "316140.KS": "WooriFinancial",
    "012330.KS": "HyundaiMobis",
    "028260.KS": "SamsungC&T",
    "032830.KS": "SamsungLife",
    "066570.KS": "LGElectronics",
    "003550.KS": "LG",
    "034730.KS": "SK",
    "096770.KS": "SKInnovation",
    "015760.KS": "KEPCO",
    "033780.KS": "KT&G",
    "017670.KS": "SKTelecom",
    "030200.KS": "KT",
    "009150.KS": "SamsungElecMech",
    "010130.KS": "KoreaZinc",
    "010950.KS": "SOil",
    "011200.KS": "HMM",
    "047050.KS": "POSCOIntl",
    "042660.KS": "HanwhaOcean",
    "009540.KS": "HDKSOE",
    "329180.KS": "HDHyundaiHeavy",
    "010140.KS": "SamsungHeavy",
    "034020.KS": "DoosanEnerbility",
    "012450.KS": "HanwhaAerospace",
    "000720.KS": "HyundaiE&C",
    "028050.KS": "SamsungE&A",
    "051900.KS": "LGH&H",
    "090430.KS": "AmorePacific",
    "097950.KS": "CJCheilJedang",
    "018260.KS": "SamsungSDS",
    "036570.KS": "NCSOFT",
    "259960.KS": "Krafton",
    "302440.KS": "SKBioscience",
    "326030.KS": "SKBiopharm",
    "128940.KS": "HanmiPharm",
    "011070.KS": "LGInnotek",
    "034220.KS": "LGDisplay",
    "004020.KS": "HyundaiSteel",
    "006260.KS": "LS",
    "010120.KS": "LSElectric",
    "071050.KS": "KoreaInvestment",
    "016360.KS": "SamsungSec",
    "024110.KS": "IBK",
    "000810.KS": "SamsungFire",
    "005830.KS": "DBInsurance",
    "138040.KS": "MeritzFinancial",
    "247540.KQ": "EcoProBM",
    "086520.KQ": "EcoPro",
    "028300.KQ": "HLB",
    "196170.KQ": "Alteogen",
    "068760.KQ": "CelltrionPharm",
    "145020.KQ": "Hugel",
    "214150.KQ": "Classys",
    "058470.KQ": "Leeno",
    "112040.KQ": "Wemade",
    "035900.KQ": "JYPEnt",
    "041510.KQ": "SM",
    "122870.KQ": "YGEnt",
    "293490.KQ": "KakaoGames",
    "263750.KQ": "PearlAbyss",
    "067160.KQ": "Medytox",
    "039030.KQ": "EO Technics",
    "036830.KQ": "Soulbrain",
    "095340.KQ": "ISC",
    "240810.KQ": "WonikIPS",
    "078340.KQ": "Com2uS",
    "060250.KQ": "NHNKCP",
    "035600.KQ": "KGInicis",
    "000250.KQ": "Samchundang",
    "084370.KQ": "EugeneTech",
    "098460.KQ": "KohYoung",
    "053030.KQ": "Binex",
    "042000.KQ": "Cafe24",
}


def now_kst() -> dt.datetime:
    return dt.datetime.now(KST)


def send_telegram(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID. Printing only.")
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
    near_high = "yes" if item["near_today_high"] else "no"
    return (
        f"<b>{item['name']} ({item['ticker']})</b>\n"
        f"score: <b>{item['score']}/9</b>\n"
        f"price: {item['last_price']:,.0f} KRW ({item['current_change_pct']:+.2f}% vs prev close)\n"
        f"open gap: {item['open_gap_pct']:+.2f}% / rebound: {item['rebound_from_open_pct']:+.2f}%\n"
        f"prev day: {item['prev_change_pct']:+.2f}% / volume x{item['prev_volume_ratio']:.1f}\n"
        f"today volume: {item['today_volume_vs_prev_pct']:.1f}% of prev day / near high: {near_high}"
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
                print(f"{ticker} skipped: empty daily or intraday data")
                continue
            item = analyze_one(ticker, name, daily, intraday, today)
            if item:
                results.append(item)
        except Exception as exc:
            print(f"{ticker} failed: {exc}")

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
    print(f"[{current_text}] morning rebound scanner started. event={EVENT_NAME}")

    if EVENT_NAME == "schedule" and current.hour >= 16:
        print("Market is closed. Scheduled run skipped.")
        return 0

    results = scan()
    if not results:
        send_telegram(
            f"📭 <b>[{current_text}] Morning rebound scanner</b>\n\n"
            "No candidates found.\n"
            "Temporary yfinance version. Best run time: 09:30-09:45 KST."
        )
        return 0

    header = (
        f"🚀 <b>[{current_text}] Morning rebound candidates</b>\n"
        f"found: <b>{len(results)}</b>\n"
        "logic: prev volume spike + morning gap + rebound\n"
    )
    messages = []
    for i in range(0, len(results), 4):
        body = "\n\n".join(format_signal(item) for item in results[i : i + 4])
        messages.append((header + "\n" if i == 0 else "") + body)

    for message in messages:
        send_telegram(message)

    print(f"sent {len(results)} candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
