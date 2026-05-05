import yfinance as yf
import pandas as pd
import requests
import os

# 1. 환경 설정 (기존과 동일)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def get_target_tickers():
    # 정환님이 관리하시는 주요 종목 리스트 (KOSPI/KOSDAQ 주요주)
    return {
        "005930.KS": "삼성전자", "000660.KS": "SK하이닉스", "005380.KS": "현대차", 
        "035420.KS": "NAVER", "000270.KS": "기아", "005490.KS": "POSCO홀딩스",
        "105560.KS": "KB금융", "055550.KS": "신한지주", "000810.KS": "삼성화재",
        "012330.KS": "현대모비스", "066570.KS": "LG전자", "032830.KS": "삼성생명",
        "011170.KS": "롯데케미칼", "004020.KS": "현대제철", "024110.KS": "기업은행"
        # ... 필요시 추가 가능
    }

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=15)

def run_value_scanner():
    ticker_dict = get_target_tickers()
    found_value_stocks = []
    
    print("💎 재무 기반 가치 퀀트 스캔 시작...")

    for ticker, name in ticker_dict.items():
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # --- 퀀트 필터링 기준 (정환님의 산업 스캐너 로직 반영) ---
            # 1. PBR (주가순자산비율): 1.0 미만 (회사가 망해도 자산이 주가보다 많음)
            pbr = info.get('priceToBook')
            # 2. PER (주가수익비율): 12 미만 (이익 대비 저평가)
            per = info.get('forwardPE') or info.get('trailingPE')
            # 3. 부채비율 (Debt to Equity): 150% 미만 (재무 건전성)
            debt_ratio = info.get('debtToEquity')

            # 필터링 로직: 저PBR 이면서 저PER인 우량주 추출
            if pbr and per and pbr < 1.0 and per < 12:
                # 부채비율 조건 (데이터가 있을 경우에만 체크)
                if debt_ratio and debt_ratio > 150:
                    continue
                
                found_value_stocks.append(
                    f"💎 *[가치 저평가 발견]*: {name}({ticker})\n"
                    f"   - PBR: {round(pbr, 2)} (자산 대비 저렴)\n"
                    f"   - PER: {round(per, 2)} (이익 대비 저렴)\n"
                    f"   - 현재가: {info.get('currentPrice', 0):,}원"
                )
                
        except Exception as e:
            print(f"Error scanning {name}: {e}")
            continue

    if found_value_stocks:
        send_msg("📢 **[재무 분석 결과] 현재 저평가된 우량주 리스트**")
        for i in range(0, len(found_value_stocks), 5):
            send_msg("\n\n".join(found_value_stocks[i:i+5]))
        print(f"✅ 가치주 {len(found_value_stocks)}건 전송 완료")
    else:
        print("🔍 조건에 맞는 가치주가 없습니다.")

if __name__ == "__main__":
    run_value_scanner()
