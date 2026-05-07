import yfinance as yf
import pandas_ta as ta
import requests
import os
import pandas as pd
import datetime  # 추가됨
import sys       # 추가됨
from zoneinfo import ZoneInfo

# 1. 환경 설정
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def check_time_and_run():
    # 한국 시간 설정
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.datetime.now(kst)
    
    # 현재 날짜와 시간을 "YYYY-MM-DD HH:MM" 형식으로 저장
    full_time_str = now_kst.strftime("%Y-%m-%d %H:%M")
    
    # [핵심] 오후 4시(16:00) 이후라면 지연 실행으로 간주하고 즉시 종료
    if now_kst.hour >= 16:
        print(f"[{full_time_str}] 장 마감 후 지연 실행 방지를 위해 종료합니다.")
        sys.exit(0)
    
    return full_time_str

# 1. 실행 시간 체크 (지연 실행 시 여기서 컷)
current_time = check_time_and_run()

def get_broad_market_tickers():
    # ... (기존 티커 맵 코드 동일) ...
    ticker_map = {
        "005930.KS": "삼성전자", "000660.KS": "SK하이닉스", "005380.KS": "현대차", "035420.KS": "NAVER",
        "000270.KS": "기아", "005490.KS": "POSCO홀딩스", "035720.KS": "카카오", "068270.KS": "셀트리온",
        # ... (생략) ...
        "084110.KQ": "휴온스", "098460.KQ": "고영"
    }
    return ticker_map

def detect_fvg(df):
    if len(df) < 3: return None
    c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    if c1['High'] < c3['Low']:
        return f"Bullish FVG (Gap: {int(c3['Low'] - c1['High']):,}원)"
    elif c1['Low'] > c3['High']:
        return f"Bearish FVG (Gap: {int(c1['Low'] - c3['High']):,}원)"
    return None

def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return round(100 - (100 / (1 + rs)).iloc[-1], 2)

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=15)

def run_fvg_scanner():
    ticker_dict = get_broad_market_tickers()
    error_tickers = ['036490.KS', '010620.KS', '032670.KS', '030190.KQ']
    tickers = [t for t in ticker_dict.keys() if t not in error_tickers]
    
    print(f"🚀 [{current_time}] 스캐너 시작!")
    
    all_data = yf.download(tickers, period="65d", interval="1d", group_by='ticker', threads=True, progress=False)
    found_signals = []
    
    for ticker in tickers:
        try:
            df = all_data[ticker].dropna()
            if len(df) < 40: continue
            
            name = ticker_dict.get(ticker, ticker)
            rsi_val = calculate_rsi(df)
            fvg_status = detect_fvg(df)
            
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()

            is_strong_buy = (macd.iloc[-2] < signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]) and ("Bullish" in str(fvg_status))
            is_buy = (macd.iloc[-1] > signal.iloc[-1] and rsi_val <= 50) and not is_strong_buy
            is_sell = (rsi_val > 70) and ("Bearish" in str(fvg_status))
            
            curr_price = int(df['Close'].iloc[-1])
            prev_price = int(df['Close'].iloc[-2])
            change_pct = round(((curr_price - prev_price) / prev_price) * 100, 2)
            change_str = f"({'+' if change_pct > 0 else ''}{change_pct}%)"

            if is_strong_buy:
                found_signals.append(f"🚀 *[매수 강추천]*: {name}({ticker})\n   *현재가*: {curr_price:,}원 {change_str}\n   *RSI*: {rsi_val} / *FVG*: {fvg_status}")
            elif is_buy:
                found_signals.append(f"🔥 *[매수 추천]*: {name}({ticker})\n   *현재가*: {curr_price:,}원 {change_str}\n   *RSI*: {rsi_val}")
            elif is_sell:
                found_signals.append(f"❄️ *[매도 추천]*: {name}({ticker})\n   *현재가*: {curr_price:,}원 {change_str}\n   *RSI*: {rsi_val}")
                
        except Exception:
            continue

    if found_signals:
        for i in range(0, len(found_signals), 5):
            send_msg("\n\n".join(found_signals[i:i+5]))
        print(f"✅ 총 {len(found_signals)}건의 신호 전송 완료!")
    else:
        # 2. 결과 없을 때도 'current_time' (한국 시간) 사용
        no_result_msg = f"🔍 *[{current_time}] 스캐너 실행 완료*\n\n현재 조건을 만족하는 종목이 없습니다."
        send_msg(no_result_msg)
        print(f"✅ 실행 완료 메시지 전송: {no_result_msg}")

if __name__ == "__main__":
    run_fvg_scanner()
