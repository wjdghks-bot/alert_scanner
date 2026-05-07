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
        "051910.KS": "LG화학", "105560.KS": "KB금융", "055550.KS": "신한지주", "000810.KS": "삼성화재",
        "012330.KS": "현대모비스", "066570.KS": "LG전자", "003550.KS": "LG", "034730.KS": "SK",
        "015760.KS": "한국전력", "033780.KS": "KT&G", "009150.KS": "삼성전기", "010130.KS": "고려아연",
        "017670.KS": "SK텔레콤", "032640.KS": "LG유플러스", "011070.KS": "LG이노텍", "016360.KS": "삼성증권",
        "000100.KS": "유한양행", "000720.KS": "현대건설", "028260.KS": "삼성물산", "036570.KS": "엔씨소프트",
        "009540.KS": "HD현대중공업", "010950.KS": "S-Oil", "011170.KS": "롯데케미칼", "004020.KS": "현대제철",
        "316140.KS": "우리금융지주", "034220.KS": "LG디스플레이", "003670.KS": "포스코퓨처엠", "086790.KS": "하나금융지주",
        "323410.KS": "카카오뱅크", "377300.KS": "카카오페이", "302440.KS": "SK바이오사이언스", "259960.KS": "크래프톤",
        "006400.KS": "삼성SDI", "096770.KS": "SK이노베이션", "030200.KS": "KT", "000640.KS": "동아쏘시오홀딩스",
        "001040.KS": "CJ", "011780.KS": "금호석유", "009830.KS": "한화솔루션", "000120.KS": "대한통운",
        "004170.KS": "신세계", "008770.KS": "호텔신라", "005935.KS": "삼성전자우", "018260.KS": "삼성에스디에스",
        "000080.KS": "하이트진로", "000150.KS": "두산", "000210.KS": "DL", "000240.KS": "한국앤컴퍼니",
        "000670.KS": "영풍", "000880.KS": "한화", "000990.KS": "DB하이텍", "001230.KS": "동국제강",
        "001430.KS": "세아베스틸지주", "001450.KS": "현대해상", "001740.KS": "SK네트웍스", "002380.KS": "KCC",
        "003490.KS": "대한항공", "004370.KS": "농심", "004990.KS": "롯데지주",
        "005830.KS": "DB손해보험", "006260.KS": "LS", "006360.KS": "GS건설", "007070.KS": "GS리테일",
        "008930.KS": "한미사이언스", "009240.KS": "한샘", "010060.KS": "OCI홀딩스", "010120.KS": "LS ELECTRIC",
        "010140.KS": "삼성중공업", "011210.KS": "현대위아", "012450.KS": "한화에어로스페이스",
        "012750.KS": "에스원", "016380.KS": "KG스틸", "020150.KS": "일진머티리얼즈", "021240.KS": "코웨이",
        "023530.KS": "롯데쇼핑", "024110.KS": "기업은행", "028050.KS": "삼성엔지니어링", "028670.KS": "팬오션",
        "032830.KS": "삼성생명", "033780.KS": "KT&G", "034020.KS": "두산에너빌리티", "035250.KS": "강원랜드",
        "036460.KS": "한국가스공사", "047040.KS": "대우건설", "047050.KS": "포스코인터내셔널", "051900.KS": "LG생활건강",
        "071050.KS": "한국금융지주", "086280.KS": "현대글로비스", "090430.KS": "아모레퍼시픽", "097950.KS": "CJ제일제당",
        "128940.KS": "한미약품", "138040.KS": "메리츠금융지주",

        # --- KOSDAQ 상위 및 주요주 ---
        "247540.KQ": "에코프로비엠", "086520.KQ": "에코프로", "066970.KS": "엘앤에프",
        "293480.KQ": "카카오게임즈", "028300.KQ": "HLB", "112040.KQ": "위메이드", "035900.KQ": "JYP Ent.",
        "214150.KQ": "클래시스", "058470.KQ": "리노공업", "145020.KQ": "휴젤", "067160.KQ": "메디톡스",
        "036830.KQ": "솔브레인", "039030.KQ": "이오테크닉스", "041510.KQ": "에스엠", "095700.KQ": "제넥신",
        "069080.KQ": "웹젠", "035600.KQ": "KG이니시스", "060250.KQ": "NHN KCP",
        "253450.KQ": "스튜디오드래곤", "056190.KQ": "에스에프에이", "025980.KQ": "아난티",
        "000250.KQ": "삼천당제약", "064550.KQ": "바이오니아", "041190.KQ": "우리기술투자",
        "086900.KQ": "메디포스트", "036200.KQ": "유진테크", "033640.KQ": "네패스", "023590.KQ": "다우기술",
        "053030.KQ": "바이넥스", "042000.KQ": "카페24", "078340.KQ": "컴투스",
        "084110.KQ": "휴온스", "098460.KQ": "고영"
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
