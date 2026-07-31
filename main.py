import os
import re
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# 파생상품, ETF, 인버스 등을 걸러내는 마법의 단어들
ETF_KEYWORDS = [
    'KODEX', 'TIGER', 'ACE', 'RISE', 'SOL', 'HANARO', 'KBSTAR', 
    'KOSEF', 'WOORI', 'PLUS', 'HERO', 'FOCUS', 'TIMEFOLIO',
    '인버스', '레버리지', 'ETN', '선물'
]

def send_telegram(message):
    """텔레그램으로 문자를 보내는 기능"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    res = requests.post(url, data=payload)
    if res.status_code != 200:
        print("텔레그램 전송 실패:", res.text)
        res.raise_for_status()

def is_etf(name):
    """이름에 파생상품 단어가 있는지 검사"""
    for word in ETF_KEYWORDS:
        if word in name:
            return True
    return False

def get_kospi():
    """1. 코스피 거래량 상위 10개 (파생상품 빼고)"""
    url = "https://finance.naver.com/sise/sise_quant.naver?sosok=0"
    res = requests.get(url, headers=HEADERS)
    res.encoding = 'euc-kr' # 한글 안 깨지게 하기
    soup = BeautifulSoup(res.text, 'html.parser')
    
    results = []
    rows = soup.select('table.type_2 tr')
    for row in rows:
        cols = row.find_all('td')
        if len(cols) > 5 and cols[1].find('a'):
            name = cols[1].get_text(strip=True)
            volume = cols[5].get_text(strip=True)
            
            # 파생상품이 아닌 진짜 주식만 바구니에 담기
            if not is_etf(name):
                results.append(f"• {name} ({volume}주)")
                if len(results) == 10:
                    break
    return results

def check_ceo(code):
    """2. 대표이사가 최대주주인지 확인하는 돋보기 기능"""
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        res = requests.get(url, headers=HEADERS)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 대표이사 이름 찾기
        ceo = ""
        summary = soup.select_one('#summary_info')
        if summary:
            match = re.search(r'대표이사\s*:\s*([^\s,]+)', summary.get_text())
            if match:
                ceo = match.group(1)
        
        # 최대주주 이름 찾기
        owner = ""
        share_table = soup.select_one('table[summary*="주요주주"]')
        if share_table:
            first_row = share_table.select_one('tbody tr')
            if first_row:
                owner = first_row.select('th')[0].get_text(strip=True)
                
        # 대표이사와 최대주주가 같은 사람인지 확인!
        if ceo and owner and (ceo in owner or owner in ceo):
            return True, ceo
    except:
        pass
    return False, ""

def get_kosdaq():
    """3. 코스닥 거래량 상위 10개 (대표이사=최대주주 조건)"""
    url = "https://finance.naver.com/sise/sise_quant.naver?sosok=1"
    res = requests.get(url, headers=HEADERS)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    results = []
    rows = soup.select('table.type_2 tr')
    for row in rows:
        cols = row.find_all('td')
        if len(cols) > 5 and cols[1].find('a'):
            name = cols[1].get_text(strip=True)
            volume = cols[5].get_text(strip=True)
            code = cols[1].find('a')['href'].split('code=')[-1]
            
            if is_etf(name): continue # 파생상품 건너뛰기
            
            # 대표이사가 최대주주인지 검사 (통과하면 바구니에 담기)
            is_valid, ceo_name = check_ceo(code)
            if is_valid:
                results.append(f"• {name} (대표: {ceo_name} / {volume}주)")
                if len(results) == 10:
                    break
    return results

def main():
    print("증권 데이터 분석 중...")
    kospi_list = get_kospi()
    kosdaq_list = get_kosdaq()
    
    msg = "<b>📊 [오늘의 주식 거래량 TOP 10]</b>\n\n"
    
    msg += "🔹 <b>1. 코스피 (파생상품 제외)</b>\n"
    msg += "\n".join(kospi_list) if kospi_list else "정보 없음"
    msg += "\n\n"
    
    msg += "👑 <b>2. 코스닥 (대표이사=최대주주)</b>\n"
    msg += "\n".join(kosdaq_list) if kosdaq_list else "정보 없음"
    
    send_telegram(msg)

if __name__ == "__main__":
    main()
