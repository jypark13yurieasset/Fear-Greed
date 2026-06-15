import os
import json
import datetime
import requests
from bs4 import BeautifulSoup
import re
import urllib3

# SSL 경고 메시지 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
}

# 1. CNN Fear and Greed 지수 가져오기
def get_fear_and_greed():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    fng_value = None
    
    try:
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            data = response.json()
            fng_value = int(round(data['fear_and_greed']['score']))
            print(f"CNN API 호출 성공! 추출한 지수: {fng_value}")
        else:
            print(f"CNN API 실패 (상태코드: {response.status_code}), 웹 스크래핑 백업 모드로 전환합니다.")
    except Exception as api_err:
        print(f"CNN API 접근 중 에러 발생: {api_err}, 웹 스크래핑 백업 모드로 전환합니다.")
        
    if fng_value is None:
        try:
            web_url = "https://edition.cnn.com/markets/fear-and-greed"
            web_response = requests.get(web_url, headers=headers, timeout=10, verify=False)
            soup = BeautifulSoup(web_response.text, 'html.parser')
            
            match = re.search(r'"ratingValue"\s*:\s*(\d+)', web_response.text)
            if match:
                fng_value = int(match.group(1))
                print(f"백업 웹 스크래핑 성공! 추출한 지수: {fng_value}")
            else:
                container = soup.find(string=re.compile(r"Fear & Greed Index is at"))
                if container:
                    fng_value = int(re.search(r'\d+', container).group())
                else:
                    raise Exception("모든 추출 경로에서 데이터를 찾지 못했습니다.")
        except Exception as web_err:
            print(f"백업 스크래핑도 실패했습니다: {web_err}")
            fng_value = 50 # 완전 실패 시 기본값 세팅
            
    return fng_value

# 2. Google Finance 데이터 가져오기 (Container: div.ujg0He, Price: div.N6SYTe, Change: div.DAicsd)
def get_google_data(name, symbol_path):
    url = f"https://www.google.com/finance/quote/{symbol_path}"
    try:
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            price_div = soup.find('div', class_='N6SYTe')
            change_div = soup.find('div', class_='DAicsd')
            
            price = None
            change_pct = None
            
            if price_div:
                price = float(price_div.text.strip().replace(',', ''))
            
            if change_div:
                span_tags = change_div.find_all('span')
                for span in span_tags:
                    text = span.text.strip()
                    if '%' in text:
                        match = re.search(r'([+-]?\d+(?:\.\d+)?)%', text)
                        if match:
                            change_pct = float(match.group(1))
                        break
            return price, change_pct
        return None, None
    except Exception as e:
        print(f"[Google] {name} 수집 에러: {e}")
        return None, None

# 3. Yahoo Finance 데이터 가져오기 (v8/finance/chart API 사용)
def get_yahoo_data(name, ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
    try:
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        if r.status_code == 200:
            data = r.json()
            res = data['chart']['result'][0]
            meta = res['meta']
            price = meta.get('regularMarketPrice')
            
            # 종가 리스트 추출
            closes = [c for c in res.get('indicators', {}).get('quote', [{}])[0].get('close', []) if c is not None]
            
            prev_close = None
            if len(closes) >= 2:
                last_close = closes[-1]
                # 마지막 데이터가 현재가와 거의 동일하면 그 전 거래일 종가 사용
                if abs(last_close - price) / price < 0.0001:
                    prev_close = closes[-2]
                else:
                    prev_close = closes[-1]
            elif len(closes) == 1:
                prev_close = closes[0]
                
            if price and prev_close:
                pct_change = (price - prev_close) / prev_close * 100
                return price, pct_change
            return price, None
        return None, None
    except Exception as e:
        print(f"[Yahoo] {name} 수집 에러: {e}")
        return None, None

# 4. 양측 데이터 수집 후 상호 검증 및 교차 체크
def get_combined_metric(name, google_path, yahoo_ticker):
    g_price, g_change = get_google_data(name, google_path)
    y_price, y_change = get_yahoo_data(name, yahoo_ticker)
    
    final_price = None
    final_change = None
    
    # 4.1 가격 결정 및 검증
    if g_price is not None and y_price is not None:
        price_diff_pct = abs(g_price - y_price) / max(g_price, y_price) * 100
        if price_diff_pct > 1.0:
            print(f"[{name}] 경고: 양방향 가격 차이 큼! Google={g_price}, Yahoo={y_price} ({price_diff_pct:.2f}%)")
        final_price = y_price # 더 정밀한 야후 데이터 선호
    elif g_price is not None:
        final_price = g_price
    elif y_price is not None:
        final_price = y_price

    # 4.2 변동률 결정 및 검증
    if g_change is not None and y_change is not None:
        change_diff = abs(g_change - y_change)
        if change_diff < 1.0: # 오차범위 1% 이내
            final_change = y_change
            print(f"[{name}] 교차 점검 성공! 최종 반영 변동률: {final_change:+.2f}% (오차: {change_diff:.4f}%)")
        else:
            final_change = g_change
            print(f"[{name}] 경고: 변동률 오차범위 초과! Google={g_change:+.2f}%, Yahoo={y_change:+.2f}%. 페이지 텍스트 기반인 Google 값 사용: {final_change:+.2f}%")
    elif g_change is not None:
        final_change = g_change
        print(f"[{name}] Yahoo 수집 실패. Google 변동률 사용: {final_change:+.2f}%")
    elif y_change is not None:
        final_change = y_change
        print(f"[{name}] Google 수집 실패. Yahoo 변동률 사용: {final_change:+.2f}%")
        
    return {
        "price": round(final_price, 2) if final_price is not None else None,
        "change": round(final_change, 2) if final_change is not None else None
    }

def main():
    today = datetime.date.today()
    today_str = today.isoformat()
    
    # 1. 주말(토요일=5, 일요일=6)인 경우 업데이트를 건너뜀
    if today.weekday() in (5, 6):
        print(f"주말({today_str})이므로 데이터를 업데이트하지 않고 건너뜁니다.")
        return
        
    json_file = "data.json"
    
    # 기존 데이터 로드
    if os.path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            try:
                dashboard_data = json.load(f)
            except json.JSONDecodeError:
                dashboard_data = {}
    else:
        dashboard_data = {}
        
    # 이전 날짜 중 가장 최근 날짜의 데이터를 찾음 (전일 데이터 carry-over용)
    sorted_dates = sorted([d for d in dashboard_data.keys() if d < today_str], reverse=True)
    prev_data = dashboard_data[sorted_dates[0]] if sorted_dates else {}
    
    print("=== CNN Fear & Greed 수집 시작 ===")
    fng_value = get_fear_and_greed()
    if fng_value is None or fng_value == 50: # 수집 실패 혹은 기본값 지정 시 직전 영업일 값 사용 시도
        if prev_data and "fear_and_greed" in prev_data:
            fng_value = prev_data["fear_and_greed"]
            print(f"CNN 수집 실패! 이전 영업일 데이터 적용: {fng_value}")
    
    print("\n=== 시장 지수 및 환율 데이터 수집 시작 (Google & Yahoo 교차 체크) ===")
    sp500 = get_combined_metric("S&P 500", ".INX:INDEXSP", "^GSPC")
    nasdaq100 = get_combined_metric("Nasdaq 100", "NDX:INDEXNASDAQ", "^NDX")
    vix = get_combined_metric("VIX", "VIX:INDEXCBOE", "^VIX")
    usd_krw = get_combined_metric("USD/KRW", "USD-KRW", "USDKRW=X")
    
    # 평일 데이터 보완 (수집 실패 시 전일/직전 영업일 데이터 그대로 적용)
    def carry_over_if_needed(metric_dict, name, price_key, change_key):
        if metric_dict["price"] is None and prev_data and price_key in prev_data:
            metric_dict["price"] = prev_data[price_key]
            print(f"[{name}] 가격 수집 실패 -> 이전 영업일 데이터 적용: {metric_dict['price']}")
        if metric_dict["change"] is None and prev_data and change_key in prev_data:
            metric_dict["change"] = prev_data[change_key]
            print(f"[{name}] 변동률 수집 실패 -> 이전 영업일 데이터 적용: {metric_dict['change']}%")

    carry_over_if_needed(sp500, "S&P 500", "sp500_price", "sp500_change")
    carry_over_if_needed(nasdaq100, "Nasdaq 100", "nasdaq100_price", "nasdaq100_change")
    carry_over_if_needed(vix, "VIX", "vix_price", "vix_change")
    carry_over_if_needed(usd_krw, "USD/KRW", "usd_krw_price", "usd_krw_change")
    
    # 데이터 업데이트
    dashboard_data[today_str] = {
        "fear_and_greed": fng_value,
        "sp500_price": sp500["price"],
        "sp500_change": sp500["change"],
        "nasdaq100_price": nasdaq100["price"],
        "nasdaq100_change": nasdaq100["change"],
        "vix_price": vix["price"],
        "vix_change": vix["change"],
        "usd_krw_price": usd_krw["price"],
        "usd_krw_change": usd_krw["change"]
    }
    
    # 혹시 모를 기존 주말(토/일) 데이터가 있다면 제거
    cleaned_dashboard_data = {}
    for d, val in dashboard_data.items():
        try:
            parsed_date = datetime.datetime.strptime(d, "%Y-%m-%d").date()
            if parsed_date.weekday() not in (5, 6): # 5 = Saturday, 6 = Sunday
                cleaned_dashboard_data[d] = val
            else:
                print(f"데이터 저장 시 기존 주말 데이터 제거: {d}")
        except Exception:
            cleaned_dashboard_data[d] = val
            
    dashboard_data = cleaned_dashboard_data
    
    # 파일 저장
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, indent=4, ensure_ascii=False)
        
    with open("data.js", "w", encoding="utf-8") as f:
        f.write(f"window.fng_data = {json.dumps(dashboard_data, indent=4, ensure_ascii=False)};\n")
        
    print(f"\n--- 작업 완료 ---")
    print(f"최종 저장 결과 -> 날짜: {today_str}")
    print(f"  CNN Fear & Greed: {fng_value}")
    print(f"  S&P 500: Price={sp500['price']}, Change={sp500['change']}%")
    print(f"  Nasdaq 100: Price={nasdaq100['price']}, Change={nasdaq100['change']}%")
    print(f"  VIX: Price={vix['price']}, Change={vix['change']}%")
    print(f"  USD/KRW: Price={usd_krw['price']}, Change={usd_krw['change']}%")


if __name__ == "__main__":
    main()
