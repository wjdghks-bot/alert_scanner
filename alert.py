import yfinance as yf
import pandas_ta as ta
import requests
import os
import pandas as pd

# 1. 환경 설정
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def get_broad_market_tickers():
    """KRX 전체 종목을 긁어오되, 안정성을 위해 상위 종목 위주로 세팅합니다."""
    try:
        url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
        df_list = pd.read_html(url, header=0)[0]
        # 종목코드와 종목명을 매핑해서 들고 있습니다.
        ticker_map = {f"{str(code).zfill(6)}.KS": name for code, name in zip(df_list['종목코드'], df_list['종목명'])}
        return ticker_map
    except:
        return {"005930.KS": "삼성전자", "000660.KS": "SK하이닉스"}

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)

def run_final_scanner():
    ticker_dict = get_broad_market_tickers()
    tickers = list(ticker_dict.keys())[:200] # 일단 상위 200개 전수 조사
    
    print(f"🚀 총 {len(tickers)}개 종목 전수 조사 시작...")
    all_data = yf.download(tickers, period="60d", interval="1d", group_by='ticker', threads=True, progress=False)
    
    found_signals = []
    
    for ticker in tickers:
        try:
            df = all_data[ticker].dropna()
            if len(df) < 35: continue

            # 지표 계산
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['EMA60'] = ta.ema(df['Close'], length=60)
            macd = ta.macd(df['Close'])
            df['MACD'] = macd['MACD_12_26_9']
            df['MACD_S'] = macd['MACDs_12_26_9']

            curr = df.iloc[-1]
            prev = df.iloc[-2]
            name = ticker_dict.get(ticker, ticker) # 종목명 가져오기

            # 🎯 SMC 타점 조건 (EMA60 위 + MACD 골든크로스)
            if curr['Close'] > curr['EMA60'] and prev['MACD'] < prev['MACD_S'] and curr['MACD'] > curr['MACD_S']:
                rsi_val = round(float(curr['RSI']), 2)
                found_signals.append(f"✅ *종목*: {name} ({ticker})\n   *현재가*: {int(curr['Close']):,}원\n   *RSI*: {rsi_val}\n   *SMC*: EMA60 돌파 완료 🚀")
        except:
            continue

    if found_signals:
        # 메시지가 너무 길면 잘릴 수 있으니 5개씩 묶어서 전송
        for i in range(0, len(found_signals), 5):
            send_msg("\n\n".join(found_signals[i:i+5]))
    else:
        print("현재 조건에 맞는 종목이 없습니다.")

if __name__ == "__main__":
    run_final_scanner()
