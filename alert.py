import yfinance as yf
import pandas_ta as ta
import requests
import time
import pandas as pd
from datetime import datetime
import os

# --- [1. 설정 영역] ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
# 9:10분 스캔을 위해 넉넉하게 9시부터 대기하도록 설정
SCHEDULED_TIMES = [(9, 10), (10, 30), (13, 30), (15, 10)]


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass


def get_extensive_tickers():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 광범위 종목 리스트 생성 중...")
    # 네이버 차단을 피하기 위해 FinanceDataReader 대신 직접 상위 종목 리스트를 구성하거나
    # 가장 안정적인 KRX 전체 리스트 백업 서버를 활용합니다.
    combined = []
    try:
        # 가장 깔끔하게 종목 리스트를 뱉어주는 공개 API를 활용 (차단 거의 없음)
        url = "https://raw.githubusercontent.com/sharebook-kr/naver-stock/master/stock_codes.csv"
        df = pd.read_csv(url, dtype={'code': str})

        # 코스피/코스닥 합쳐서 약 500개만 선별 (속도와 안정성 위해)
        for _, row in df.head(500).iterrows():
            code = row['code']
            name = row['name']
            # 보통 0으로 시작하면 코스피, 나머지는 체크가 필요하지만 간단히 suffix 처리
            # (yfinance는 .KS나 .KQ 둘 다 시도해보는 로직을 내부에 갖고 있음)
            combined.append((code, name))
        return combined
    except:
        print("공공 리스트 확보 실패, 비상용 리스트 사용")
        return [('005930', '삼성전자'), ('000660', 'SK하이닉스')]  # 최소 방어선


def scan_logic(ticker, name):
    # 코스피(.KS)로 먼저 시도해보고 안되면 코스닥(.KQ)으로 시도하는 듀얼 체크
    for suffix in ['KS', 'KQ']:
        try:
            full_ticker = f"{ticker}.{suffix}"
            df = yf.download(full_ticker, period="150d", interval="1d", progress=False, timeout=5)

            if df is None or len(df) < 60: continue  # 데이터 없으면 다음 suffix로
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # 지표 계산
            df['EMA60'] = ta.ema(df['Close'], length=60)
            macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
            df['MACD'] = macd.iloc[:, 0]
            df['MACD_S'] = macd.iloc[:, 2]

            curr = df.iloc[-1]
            prev = df.iloc[-2]

            # 필터: 60일선 위 + MACD 골든크로스 + 거래대금(테스트 위해 1억으로 설정)
            curr_value = float(curr['Close'] * curr['Volume'])

            if curr['Close'] > curr['EMA60'] and (prev['MACD'] < prev['MACD_S']) and (curr['MACD'] > curr['MACD_S']):
                if curr_value > 100000000:  # 1억 이상 (실전엔 300억으로 수정)
                    has_fvg = False
                    if len(df) >= 3:
                        if df['Low'].iloc[-1] > df['High'].iloc[-3]: has_fvg = True

                    fvg_icon = "✅ FVG" if has_fvg else "❌ FVG"
                    change_rate = ((curr['Close'] - prev['Close']) / prev['Close']) * 100

                    msg = f"🚀 *[광범위 포착]* `{name}`\n금액: {float(curr['Close']):,.0f}원 ({change_rate:+.2f}%)\n대금: {curr_value / 100000000:,.1f}억 / {fvg_icon}"
                    send_telegram(msg)
                    print(f"[!] {name} ({full_ticker}) 발견")
                    return  # 하나라도 성공하면 다음 종목으로
        except:
            continue


if __name__ == "__main__":
    print("🚀 광범위 스캐너 가동 (차단 방지 모드)")

    # 1. 즉시 실행 테스트 (전체 500개 스캔)
    ticker_list = get_extensive_tickers()
    if ticker_list:
        print(f"✅ {len(ticker_list)}개 종목을 로드했습니다. 즉시 스캔을 시작합니다.")
        for ticker, name in ticker_list:
            scan_logic(ticker, name)
            time.sleep(0.05)  # 속도를 위해 딜레이 단축
        print(f"✨ [{datetime.now().strftime('%H:%M')}] 첫 전체 스캔 완료.")

    already_done = []
    print(f"\n💡 이제부터 예약 모드입니다. (컴퓨터를 끄지 마세요)")

    while True:
        now = datetime.now()
        current_time = (now.hour, now.minute)
        if current_time in SCHEDULED_TIMES and current_time not in already_done:
            print(f"🔔 {current_time} 정기 스캔 시작!")
            ticker_list = get_extensive_tickers()
            for ticker, name in ticker_list:
                scan_logic(ticker, name)
                time.sleep(0.05)
            already_done.append(current_time)

        if now.hour == 0 and now.minute == 0: already_done = []
        time.sleep(30)
