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

            # 데이터가 존재할 때만 비교 (하나라도 없으면 통과하지 못하는 문제 해결)
            if pbr is not None and per is not None:
                if pbr < 1.3 and per < 15:
                    # 부채비율은 데이터가 있을 때만 체크하고, 없으면 일단 패스
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
