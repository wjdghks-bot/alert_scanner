import yfinance as yf
import pandas as pd
import requests
import os
import datetime  # 추가
import sys       # 추가
from zoneinfo import ZoneInfo

# 1. 환경 설정
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def check_time_and_run():
    # 한국 시간 설정
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.datetime.now(kst)
    
    # 현재 시간을 "YYYY-MM-DD HH:MM" 형식으로 저장
    full_time_str = now_kst.strftime("%Y-%m-%d %H:%M")
    
    # [핵심] 오후 4시(16:00) 이후라면 지연 실행으로 간주하고 즉시 종료
    if now_kst.hour >= 16:
        print(f"[{full_time_str}] 장 마감 후 지연 실행 방지를 위해 종료합니다.")
        sys.exit(0)
    
    return full_time_str

# 1. 실행 시간 체크 (여기서 16시 이후면 컷!)
current_time = check_time_and_run()

def get_target_tickers():
    return {
        # --- KOSPI 상위 및 주요주 ---
        "005930.KS": "삼성전자", "000660.KS": "SK하이닉스", "005380.KS": "현대차", "035420.KS": "NAVER",
        "000270.KS": "기아", "005490.KS": "POSCO홀딩스", "035720.KS": "카카오", "068270.KS": "셀트리온",
        # ... (중략 - 기존 티커 리스트 동일) ...
        "084110.KQ": "휴온스", "098460.KQ": "고영"
    }

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=15)

def run_value_scanner():
    ticker_dict = get_target_tickers()
    found_value_stocks = []
    
    print(f"💎 [{current_time}] 재무 기반 가치 퀀트 스캔 시작...")

    for ticker, name in ticker_dict.items():
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            pbr = info.get('priceToBook')
            per = info.get('forwardPE') or info.get('trailingPE')
            debt_ratio = info.get('debtToEquity')

            if pbr is not None and per is not None:
                if pbr < 1.3 and per < 15:
                    if debt_ratio and debt_ratio > 150:
                        continue
                
                    found_value_stocks.append(
                        f"💎 *[가치 저평가 발견]*: {name}({ticker})\n"
                        f"   - PBR: {round(pbr, 2)} / PER: {round(per, 2)}\n"
                        f"   - 현재가: {info.get('currentPrice', 0):,}원"
                    )
                
        except Exception as e:
            continue

    # 결과 전송 로직 (KST 시간인 current_time 사용)
    if found_value_stocks:
        send_msg(f"📢 **[재무 분석 결과 - {current_time}] 저평가 우량주**")
        for i in range(0, len(found_value_stocks), 5):
            send_msg("\n\n".join(found_value_stocks[i:i+5]))
        print(f"✅ 가치주 {len(found_value_stocks)}건 전송 완료")
    else:
        # 조건에 맞는 종목이 없을 때도 한국 시간으로 알림
        no_result_text = f"🔍 *[{current_time}] 재무 스캐너 실행 완료*\n\n현재 조건을 만족하는 가치주가 없습니다."
        send_msg(no_result_text)
        print("🔍 조건에 맞는 가치주가 없어 알람을 보냈습니다.")

if __name__ == "__main__":
    run_value_scanner()
