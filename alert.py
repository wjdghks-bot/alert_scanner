import yfinance as yf
import pandas_ta as ta
import requests
import os
import pandas as pd

# 1. 환경 설정
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def get_broad_market_tickers():
    ticker_map = {
        # --- KOSPI 상위 및 주요주 ---
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
    
    print(f"🚀 비대칭 전략 모드 시작! (매수 완화 / 매도 강화)")
    
    all_data = yf.download(tickers, period="65d", interval="1d", group_by='ticker', threads=True, progress=False)
    found_signals = []
    
    for ticker in tickers:
        try:
            df = all_data[ticker].dropna()
            if len(df) < 40: continue
            
            name = ticker_dict.get(ticker, ticker)
            curr = df.iloc[-1]
            
            # --- 지표 계산 로직 ---
            rsi_val = calculate_rsi(df)
            fvg_status = detect_fvg(df)
            
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            # --- [4단계 정밀 필터링 로직] ---
            
            # 1. 매수 강추천 (Strong Buy): MACD 골든크로스 + Bullish FVG (신뢰도 최상)
            is_strong_buy = (macd.iloc[-2] < signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]) and \
                            ("Bullish" in str(fvg_status))
            
            # 2. 매수 추천 (Buy): MACD 상승 추세 유지 + RSI 50 이하 (눌림목/저평가)
            is_buy = (macd.iloc[-1] > signal.iloc[-1] and rsi_val <= 50) and not is_strong_buy
            
            # 3. 매도 추천 (Sell): RSI 80 초과 + Bearish FVG 발생 (탈출 신호)
            is_sell = (rsi_val > 80) and ("Bearish" in str(fvg_status))

            if is_strong_buy:
                found_signals.append(
                    f"🚀 *[매수 강추천]*: {name}({ticker})\n"
                    f"   *구분*: 골든크로스 + SMC 지지 확인 🎯\n"
                    f"   *RSI*: {rsi_val} / *FVG*: {fvg_status}"
                )
            
            elif is_buy:
                found_signals.append(
                    f"🔥 *[매수 추천]*: {name}({ticker})\n"
                    f"   *구분*: 저평가 구간 추세 상승 📈\n"
                    f"   *RSI*: {rsi_val} / *FVG*: {fvg_status if fvg_status else '없음'}"
                )

            elif is_sell:
                found_signals.append(
                    f"❄️ *[매도 추천]*: {name}({ticker})\n"
                    f"   *구분*: 강력 과열 및 하락 징후 ⚠️\n"
                    f"   *RSI*: {rsi_val} / *FVG*: {fvg_status}"
                )

                
        except Exception:
            continue

    if found_signals:
        for i in range(0, len(found_signals), 5):
            send_msg("\n\n".join(found_signals[i:i+5]))
        print(f"✅ 총 {len(found_signals)}건의 신호 전송 완료!")
    else:
        print("🔍 현재 조건을 만족하는 종목이 없습니다.")

if __name__ == "__main__":
    run_fvg_scanner()
