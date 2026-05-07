import yfinance as yf
import pandas_ta as ta
import requests
import os
import pandas as pd
import datetime
import sys
from zoneinfo import ZoneInfo

# 1. 환경 설정
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def check_time_and_run():
    event_name = os.getenv('GITHUB_EVENT_NAME', 'manual') 
    
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.datetime.now(kst)
    full_time_str = now_kst.strftime("%Y-%m-%d %H:%M")
    
    if event_name == 'schedule':
        if now_kst.hour >= 16:
            print(f"[{full_time_str}] 스케줄러 지연 실행 방지를 위해 종료합니다.")
            sys.exit(0)
    
    print(f"[{full_time_str}] 스캐너를 시작합니다. (실행 모드: {event_name})")
    return full_time_str

current_time = check_time_and_run()

def get_broad_market_tickers():
    # 티커 리스트 (기존과 동일)
    ticker_map = {
        "005930.KS": "삼성전자", "000660.KS": "SK하이닉스", "005380.KS": "현대차", "035420.KS": "NAVER",
        "000270.KS": "기아", "005490.KS": "POSCO홀딩스", "035720.KS": "카카오", "068270.KS": "셀트리온",
        "003490.KS": "대한항공", # 여기에 대한항공이 포함되어 있어야 합니다.
        # ... 나머지 생략 ...
    }
    return ticker_map

def detect_fvg(df):
    if len(df) < 3: return None
    # 최신 3개의 봉 추출 (.item()으로 단일 수치 변환)
    c1_high = df['High'].iloc[-3].item()
    c1_low = df['Low'].iloc[-3].item()
    c3_high = df['High'].iloc[-1].item()
    c3_low = df['Low'].iloc[-1].item()
    
    if c1_high < c3_low:
        return f"Bullish FVG (Gap: {int(c3_low - c1_high):,}원)"
    elif c1_low > c3_high:
        return f"Bearish FVG (Gap: {int(c1_low - c3_high):,}원)"
    return None

def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi.iloc[-1].item(), 2)

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=15)

def run_fvg_scanner():
    ticker_dict = get_broad_market_tickers()
    tickers = list(ticker_dict.keys())
    
    print(f"🚀 [{current_time}] 스캐너 시작!")
    
    # 1. 일괄 다운로드 후 데이터 정제 (group_by='ticker' 필수)
    all_data = yf.download(tickers, period="65d", interval="1d", group_by='ticker', threads=True, progress=False)
    found_signals = []
    
    for ticker in tickers:
        try:
            # 2. 개별 종목 데이터 분리 및 NaN 제거
            if ticker in all_data:
                df = all_data[ticker].dropna()
            else:
                continue
                
            if len(df) < 30: continue
            
            name = ticker_dict.get(ticker, ticker)
            
            # 3. 지표 계산 (.item() 등을 활용해 확실한 단일 값 추출)
            rsi_val = calculate_rsi(df)
            fvg_status = detect_fvg(df)
            
            close_prices = df['Close']
            exp1 = close_prices.ewm(span=12, adjust=False).mean()
            exp2 = close_prices.ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()

            # 수치 변환 (판정 오류 방지)
            m_curr, s_curr = macd.iloc[-1].item(), signal.iloc[-1].item()
            m_prev, s_prev = macd.iloc[-2].item(), signal.iloc[-2].item()

            # 판정 로직
            is_strong_buy = (m_prev < s_prev and m_curr > s_curr) and ("Bullish" in str(fvg_status))
            is_buy = (m_curr > s_curr and rsi_val <= 50) and not is_strong_buy
            is_sell = (rsi_val > 70) and ("Bearish" in str(fvg_status))
            
            curr_price = int(close_prices.iloc[-1].item())
            prev_price = int(close_prices.iloc[-2].item())
            change_pct = round(((curr_price - prev_price) / prev_price) * 100, 2)
            change_str = f"({'+' if change_pct > 0 else ''}{change_pct}%)"

            if is_strong_buy:
                found_signals.append(f"🚀 *[매수 강추천]*: {name}({ticker})\n   *현재가*: {curr_price:,}원 {change_str}\n   *RSI*: {rsi_val} / *FVG*: {fvg_status}")
            elif is_buy:
                found_signals.append(f"🔥 *[매수 추천]*: {name}({ticker})\n   *현재가*: {curr_price:,}원 {change_str}\n   *RSI*: {rsi_val}")
            elif is_sell:
                found_signals.append(f"❄️ *[매도 추천]*: {name}({ticker})\n   *현재가*: {curr_price:,}원 {change_str}\n   *RSI*: {rsi_val}")
                
        except Exception as e:
            print(f"Error analyzing {ticker}: {e}")
            continue

    if found_signals:
        for i in range(0, len(found_signals), 5):
            send_msg("\n\n".join(found_signals[i:i+5]))
        print(f"✅ 총 {len(found_signals)}건의 신호 전송 완료!")
    else:
        no_result_msg = f"🔍 *[{current_time}] 스캐너 실행 완료*\n\n현재 조건을 만족하는 종목이 없습니다."
        send_msg(no_result_msg)
        print(f"✅ 실행 완료 메시지 전송")

if __name__ == "__main__":
    run_fvg_scanner()
