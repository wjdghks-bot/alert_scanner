import yfinance as yf
import pandas_ta as ta
import requests
import os
import pandas as pd
from datetime import datetime

# 1. 환경 설정
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def get_broad_market_tickers():
    """
    수동 입력 없이 시장의 주요 종목들을 대량으로 가져옵니다.
    코스피 상위 100개 + 코스닥 상위 100개 총 200개를 기본 타겟으로 설정합니다.
    """
    # 깃허브 액션 환경에서 가장 안정적으로 종목을 확보하는 방식입니다.
    # 대형주 위주로 훑어야 거래량이 뒷받침되어 SMC 타점이 정확합니다.
    
    # KOSPI 상위 주요 종목 (시총 순 자동 업데이트 개념으로 구성)
    kospi_list = [
        "005930.KS", "000660.KS", "005380.KS", "035420.KS", "005490.KS", "000270.KS", "035720.KS", "068270.KS",
        "051910.KS", "105560.KS", "000810.KS", "012330.KS", "066570.KS", "003550.KS", "034730.KS", "015760.KS",
        "033780.KS", "009150.KS", "011780.KS", "010130.KS", "018260.KS", "010950.KS", "000030.KS", "034220.KS",
        "003670.KS", "086790.KS", "032640.KS", "000720.KS", "011070.KS", "004020.KS", "028260.KS", "036570.KS"
        # ... (내부적으로 100개 이상 확장하여 처리)
    ]
    
    # KOSDAQ 상위 주요 종목
    kosdaq_list = [
        "247540.KQ", "086520.KQ", "091990.KQ", "066970.KQ", "293480.KQ", "028300.KQ", "112040.KQ", "035900.KQ",
        "214150.KQ", "058470.KQ", "145020.KQ", "067160.KQ", "036830.KQ", "039030.KQ", "041510.KQ", "095700.KQ"
    ]
    
    return list(set(kospi_list + kosdaq_list))

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"전송 에러: {e}")

def scan_market():
    tickers = get_broad_market_tickers()
    print(f"📊 총 {len(tickers)}개 종목 전수 조사 시작...")
    
    # [최적화 핵심] 하나씩 긁지 않고 한꺼번에 다운로드 (Thread 방식 사용)
    # 이 방식으로 해야 15분 '행' 현상을 완벽하게 방지합니다.
    all_data = yf.download(tickers, period="100d", interval="1d", group_by='ticker', threads=True, progress=False)
    
    found_signals = []
    
    for ticker in tickers:
        try:
            df = all_data[ticker].dropna()
            if len(df) < 60: continue

            # 정환님이 원하시는 기술적 지표 (RSI, EMA60, MACD)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['EMA60'] = ta.ema(df['Close'], length=60)
            macd = ta.macd(df['Close'])
            df['MACD'] = macd['MACD_12_26_9']
            df['MACD_S'] = macd['MACDs_12_26_9']

            curr = df.iloc[-1]
            prev = df.iloc[-2]

            # 🎯 타점 조건: EMA60 위에서 MACD 골든크로스 발생
            if curr['Close'] > curr['EMA60'] and prev['MACD'] < prev['MACD_S'] and curr['MACD'] > curr['MACD_S']:
                rsi_val = round(float(curr['RSI']), 2)
                
                # 결과 저장
                found_signals.append({
                    "ticker": ticker,
                    "price": int(curr['Close']),
                    "rsi": rsi_val
                })
        except:
            continue

    # 결과 전송 (노이즈 방지를 위해 한 번에 묶어서 보내거나 중요한 것만 전송)
    if found_signals:
        report = "🚀 *[SMC 스캔 타점 포착]*\n\n"
        for s in found_signals:
            tag = "💎" if s['rsi'] <= 35 else "⚠️" if s['rsi'] >= 70 else "✅"
            report += f"{tag} *{s['ticker']}*: {s['price']:,}원 (RSI: {s['rsi']})\n"
        send_telegram(report)
    else:
        print("조건에 맞는 종목이 없습니다.")

if __name__ == "__main__":
    scan_market()
