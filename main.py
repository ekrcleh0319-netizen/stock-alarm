import os
import re
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

ETF_KEYWORDS = [
    'KODEX', 'TIGER', 'ACE', 'RISE', 'SOL', 'HANARO', 'KBSTAR', 
    'KOSEF', 'WOORI', 'PLUS', 'HERO', 'FOCUS', 'TIMEFOLIO',
    '인버스', '레버리지', 'ETN', '선물'
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    res = requests.post(url, data=payload)
    if res.status_code != 200:
        print("텔레그램 전송 실패:", res.text)
        res.raise_for_status()

def is_etf(name):
    for word in ETF_KEYWORDS:
        if word in name:
            return True
    return False

def get_kospi():
    url = "https://finance.naver.com/sise/sise_quant.naver?sosok=0"
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
            
            if not is_etf(name):
                results.append(f"• {name} ({volume}주)")
                if len(results) == 10:
                    break
    return results

def check_ceo(code, name):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        res = requests.get(url, headers=HEADERS)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        ceo = ""
        # 팩트 체크 완료: #summary_info (ID)가 아니라 .summary_info (Class)가 맞습니다.
        summary = soup.select_one('.summary_info')
        if summary:
            match = re.search(r'대표이사\s*:\s*([^\s,]+)', summary.get_text())
            if match:
                ceo = match.group(1)
        
        owner = ""
        share_table = soup.select_one('table[summary*="주요주주"]')
        if share_table:
            first_row = share_table.select_one('tbody tr')
            if first_row:
                # th나 td 모두에서 텍스트를 확실히 가져오도록 보완
                owner_tag = first_row.select_one('th, td')
                if owner_tag:
                    owner = owner_tag.get_text(strip=True)
        
        # 깃허브 Actions 로그에서 로봇이 제대로 찾고 있는지 확인하기 위한 출력문
        print(f"탐색중 [{name}] - 대표이사: {ceo} / 최대주주: {owner}")
                
        if ceo and owner and (ceo in owner or owner in ceo):
            return True, ceo
    except Exception as e:
        print(f"[{name}] 분석 중 오류: {e}")
        
    return False, ""

def get_kosdaq():
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
            
            if is_etf(name): continue 
            
            is_valid, ceo_name = check_ceo(code, name)
            if is_valid:
                results.append(f"• {name} (대표: {ceo_name} / {volume}주)")
                if len(results) == 10:
                    break
    return results

def main():
    print("=== 증권 데이터 수집 시작 ===")
    kospi_list = get_kospi()
    print("--- 코스닥 대표이사 검증 시작 ---")
    kosdaq_list = get_kosdaq()
    
    msg = "<b>📊 [오늘의 주식 거래량 TOP 10]</b>\n\n"
    
    msg += "🔹 <b>1. 코스피 (파생상품 제외)</b>\n"
    msg += "\n".join(kospi_list) if kospi_list else "정보 없음"
    msg += "\n\n"
    
    msg += "👑 <b>2. 코스닥 (대표이사=최대주주)</b>\n"
    msg += "\n".join(kosdaq_list) if kosdaq_list else "조건에 맞는 종목이 없습니다."
    
    send_telegram(msg)
    print("=== 모든 작업 완료 ===")

if __name__ == "__main__":
    main()
