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

# AAII Investor Sentiment Survey 데이터 가져오기
def get_aaii_sentiment():
    """AAII 주간 투자 심리 설문 데이터를 스크래핑합니다.
    매주 수요일(미국 현지시간) 업데이트됩니다.
    Returns: dict with keys: bullish, neutral, bearish, date (or None if failed)
    """
    url = "https://www.aaii.com/sentimentsurvey"
    try:
        r = requests.get(url, headers=headers, timeout=15, verify=False)
        if r.status_code == 200:
            text = r.text
            
            # JavaScript 변수에서 전체 투표 수치 추출
            bull_match = re.search(r'var\s+bullTotalCnt\s*=\s*([\d.]+)', text)
            neutral_match = re.search(r'var\s+neutralTotalCnt\s*=\s*([\d.]+)', text)
            bear_match = re.search(r'var\s+bearTotalCnt\s*=\s*([\d.]+)', text)
            
            if bull_match and neutral_match and bear_match:
                bullish = round(float(bull_match.group(1)), 1)
                neutral = round(float(neutral_match.group(1)), 1)
                bearish = round(float(bear_match.group(1)), 1)
                
                # dataChart5 배열에서 가장 최근 날짜 추출
                date_matches = re.findall(r'"date_":\s*"(\d{4}-\d{2}-\d{2})"', text)
                survey_date = date_matches[-1] if date_matches else None
                
                print(f"AAII 수집 성공! Bullish={bullish}%, Neutral={neutral}%, Bearish={bearish}%, 설문 마감일={survey_date}")
                return {
                    "bullish": bullish,
                    "neutral": neutral,
                    "bearish": bearish,
                    "date": survey_date
                }
            else:
                # 백업: HTML 바 차트에서 가장 최근 주의 데이터 추출
                soup = BeautifulSoup(text, 'html.parser')
                weekending_divs = soup.find_all('div', class_='weekending')
                for div in weekending_divs:
                    bars = div.find_all('div', class_='bar')
                    if len(bars) >= 3:
                        bullish = float(bars[0].text.strip().replace('%', ''))
                        neutral = float(bars[1].text.strip().replace('%', ''))
                        bearish = float(bars[2].text.strip().replace('%', ''))
                        date_div = div.find('div', class_='date')
                        survey_date = None
                        if date_div:
                            date_text = date_div.text.strip()
                            # 날짜 형식 M/D/YYYY -> YYYY-MM-DD 변환
                            try:
                                parsed = datetime.datetime.strptime(date_text, '%m/%d/%Y').date()
                                survey_date = parsed.isoformat()
                            except:
                                pass
                        print(f"AAII 백업 추출 성공! Bullish={bullish}%, Neutral={neutral}%, Bearish={bearish}%")
                        return {
                            "bullish": bullish,
                            "neutral": neutral,
                            "bearish": bearish,
                            "date": survey_date
                        }
                print("AAII 페이지에서 데이터를 찾지 못했습니다.")
                return None
        else:
            print(f"AAII 페이지 접근 실패 (상태코드: {r.status_code})")
            return None
    except Exception as e:
        print(f"AAII 수집 에러: {e}")
        return None

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

def get_finviz_dxy():
    """Finviz futures 페이지에서 U.S. Dollar Index (DX) 가격과 변동률을 수집합니다."""
    url = "https://finviz.com/futures.ashx"
    try:
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        if r.status_code == 200:
            html = r.text
            dx_match = re.search(r'"DX":(\{.*?\})', html)
            if dx_match:
                dx_block = dx_match.group(1)
                last_match = re.search(r'"last":\s*([\d.]+)', dx_block)
                change_match = re.search(r'"change":\s*([-\d.]+)', dx_block)
                
                if last_match and change_match:
                    price = float(last_match.group(1))
                    change = float(change_match.group(1))
                    print(f"[Finviz] DXY 수집 성공! Price: {price}, Change: {change}%")
                    return price, change
        print("[Finviz] U.S. Dollar Index 수집 실패")
        return None, None
    except Exception as e:
        print(f"[Finviz] DXY 수집 중 에러 발생: {e}")
        return None, None

def get_dxy_metric():
    """Yahoo Finance와 Finviz의 DXY 데이터를 수집하여 상호 검증 후 최종 반영합니다."""
    f_price, f_change = get_finviz_dxy()
    y_price, y_change = get_yahoo_data("DXY", "DX-Y.NYB")
    
    final_price = None
    final_change = None
    
    # 가격 검증
    if f_price is not None and y_price is not None:
        price_diff_pct = abs(f_price - y_price) / max(f_price, y_price) * 100
        if price_diff_pct > 1.0:
            print(f"[DXY] 경고: 양방향 가격 차이 큼! Finviz={f_price}, Yahoo={y_price} ({price_diff_pct:.2f}%)")
        final_price = y_price # 야후가 조금 더 정밀(소수점 셋째 자리)하므로 야후 선호
    elif f_price is not None:
        final_price = f_price
    elif y_price is not None:
        final_price = y_price
        
    # 변동률 검증
    if f_change is not None and y_change is not None:
        change_diff = abs(f_change - y_change)
        if change_diff < 1.0:
            final_change = y_change
            print(f"[DXY] 교차 점검 성공! 최종 반영 변동률: {final_change:+.2f}% (오차: {change_diff:.4f}%)")
        else:
            final_change = f_change
            print(f"[DXY] 경고: 변동률 오차범위 초과! Finviz={f_change:+.2f}%, Yahoo={y_change:+.2f}%. Finviz 값 사용: {final_change:+.2f}%")
    elif f_change is not None:
        final_change = f_change
        print(f"[DXY] Yahoo 수집 실패. Finviz 변동률 사용: {final_change:+.2f}%")
    elif y_change is not None:
        final_change = y_change
        print(f"[DXY] Finviz 수집 실패. Yahoo 변동률 사용: {final_change:+.2f}%")
        
    return {
        "price": round(final_price, 2) if final_price is not None else None,
        "change": round(final_change, 2) if final_change is not None else None
    }

import urllib.request

def get_assets_by_market_cap():
    """companiesmarketcap.com에서 글로벌 자산 시가총액 TOP 20 데이터를 수집합니다."""
    url = "https://companiesmarketcap.com/assets-by-market-cap/"
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8')
            
            tbody_match = re.search(r'<tbody[^>]*>(.*?)</tbody>', html, re.DOTALL)
            tbody_html = tbody_match.group(1) if tbody_match else html
                
            tr_blocks = re.findall(r'<tr[^>]*>(.*?)</tr>', tbody_html, re.DOTALL)
            
            assets = []
            for tr in tr_blocks:
                rank_match = re.search(r'class="rank-td[^"]*"[^>]*>\s*(\d+)', tr)
                name_match = re.search(r'class="company-name">([^<]+)</div>', tr)
                code_match = re.search(r'class="company-code">(?:<span[^>]*></span>)?\s*([^<]+?)\s*</div>', tr)
                mcap_match = re.search(r'<td class="td-right"[^>]*data-sort="\d+">\s*(\$[^<]+)\s*</td>', tr)
                
                if rank_match and name_match and mcap_match:
                    rank = int(rank_match.group(1).strip())
                    name = name_match.group(1).strip()
                    code = code_match.group(1).strip() if code_match else "N/A"
                    mcap = mcap_match.group(1).strip()
                    
                    assets.append({
                        "rank": rank,
                        "name": name,
                        "code": code,
                        "mcap": mcap
                    })
                    if len(assets) >= 20:
                        break
            
            if assets:
                print(f"글로벌 자산 시가총액 TOP 20 수집 성공! ({len(assets)}개)")
                return assets
            else:
                print("글로벌 자산 시가총액 데이터를 파싱하지 못했습니다.")
                return None
    except Exception as e:
        print(f"글로벌 자산 시가총액 수집 중 에러 발생: {e}")
        return None

def get_koact_holdings():
    print("Scraping KoAct...")
    try:
        # Directly query the specific ETF's API endpoint used by the webpage
        detail_url = "https://www.samsungactive.co.kr/api/v1/product/etf/2ETFQ1.do"
        r = requests.get(detail_url, headers=headers, timeout=10, verify=False)
        r.raise_for_status()
        
        data = r.json()
        pdf_data = data.get('pdf', {})
        
        gijun_date = pdf_data.get('gijunYMD')
        if not gijun_date:
            print("Could not find gijunYMD from KoAct API.")
            return None
            
        print(f"Latest KoAct date: {gijun_date}")
        
        pdf_list = pdf_data.get('list', [])
        
        holdings = []
        for item in pdf_list:
            ratio_str = item.get('ratio')
            name = item.get('secNm', '').strip()
            itm_no = item.get('itmNo', '')
            # Filter out cash and empty ratios
            if ratio_str and name and not any(k in name for k in ['현금', 'CASH', '원화', '설정']):
                try:
                    weight = float(ratio_str)
                    if weight > 0:
                        ticker = ''
                        if itm_no:
                            ticker = itm_no.strip().split()[0].upper()
                        holdings.append({
                            'name': name,
                            'ticker': ticker,
                            'weight': weight
                        })
                except ValueError:
                    pass
                    
        # Sort by weight descending
        holdings.sort(key=lambda x: x['weight'], reverse=True)
        top10 = holdings[:10]
        
        # Format date from YYYYMMDD to YYYY.MM.DD
        formatted_date = f"{gijun_date[:4]}.{gijun_date[4:6]}.{gijun_date[6:]}"
        
        return {
            'date': formatted_date,
            'holdings': top10
        }
    except Exception as e:
        print(f"Error scraping KoAct: {e}")
        return None

def get_timefolio_holdings():
    print("Scraping Timefolio...")
    try:
        url = "https://timeetf.co.kr/m11_view.php?idx=2&cate="
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        
        tables = soup.find_all('table')
        if len(tables) < 3:
            print("Timefolio page does not have enough tables.")
            return None
            
        # Table 0 is holdings
        holdings_table = tables[0]
        rows = holdings_table.find_all('tr')
        holdings = []
        for r in rows[1:]: # skip header
            cells = [c.get_text(strip=True) for c in r.find_all('td')]
            if len(cells) >= 5:
                ticker_raw = cells[0]
                name = cells[1]
                weight_str = cells[4]
                try:
                    weight = float(weight_str)
                    ticker = ''
                    if ticker_raw:
                        ticker = ticker_raw.strip().split()[0].upper()
                    holdings.append({
                        'name': name,
                        'ticker': ticker,
                        'weight': weight
                    })
                except ValueError:
                    pass
        # Top 10
        top10 = holdings[:10]
        
        # 기준일을 스크래핑한 과거 날짜가 아닌 '오늘 날짜(업데이트 실행일)'로 설정
        import datetime
        date_str = datetime.date.today().strftime("%Y.%m.%d")
            
        return {
            'date': date_str,
            'holdings': top10
        }
    except Exception as e:
        print(f"Error scraping Timefolio: {e}")
        return None

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
    
    print("\n=== AAII Investor Sentiment Survey 수집 시작 ===")
    aaii_data = get_aaii_sentiment()
    if aaii_data is None:
        if prev_data and "aaii_bullish" in prev_data:
            aaii_data = {
                "bullish": prev_data["aaii_bullish"],
                "neutral": prev_data["aaii_neutral"],
                "bearish": prev_data["aaii_bearish"],
                "date": prev_data.get("aaii_date")
            }
            print(f"AAII 수집 실패! 이전 데이터 적용: Bullish={aaii_data['bullish']}%, Bearish={aaii_data['bearish']}%")
    
    print("\n=== 시장 지수 및 환율 데이터 수집 시작 (Google & Yahoo 교차 체크) ===")
    sp500 = get_combined_metric("S&P 500", ".INX:INDEXSP", "^GSPC")
    nasdaq = get_combined_metric("Nasdaq Composite", ".IXIC:INDEXNASDAQ", "^IXIC")
    vix = get_combined_metric("VIX", "VIX:INDEXCBOE", "^VIX")
    dxy = get_dxy_metric()
    
    # 평일 데이터 보완 (수집 실패 시 전일/직전 영업일 데이터 그대로 적용)
    def carry_over_if_needed(metric_dict, name, price_key, change_key):
        if metric_dict["price"] is None and prev_data and price_key in prev_data:
            metric_dict["price"] = prev_data[price_key]
            print(f"[{name}] 가격 수집 실패 -> 이전 영업일 데이터 적용: {metric_dict['price']}")
        if metric_dict["change"] is None and prev_data and change_key in prev_data:
            metric_dict["change"] = prev_data[change_key]
            print(f"[{name}] 변동률 수집 실패 -> 이전 영업일 데이터 적용: {metric_dict['change']}%")

    carry_over_if_needed(sp500, "S&P 500", "sp500_price", "sp500_change")
    carry_over_if_needed(nasdaq, "Nasdaq Composite", "nasdaq_price", "nasdaq_change")
    carry_over_if_needed(vix, "VIX", "vix_price", "vix_change")
    carry_over_if_needed(dxy, "DXY", "dxy_price", "dxy_change")
    
    print("\n=== 글로벌 자산 시가총액 TOP 20 수집 시작 ===")
    assets_top20 = get_assets_by_market_cap()
    if assets_top20 is None:
        if prev_data and "assets_top20" in prev_data:
            assets_top20 = prev_data["assets_top20"]
            print("글로벌 자산 수집 실패 -> 이전 영업일 데이터 적용")

    print("\n=== Active ETF Holdings 수집 시작 ===")
    koact_holdings = get_koact_holdings()
    if koact_holdings is None:
        if prev_data and "koact_holdings" in prev_data:
            koact_holdings = {
                "date": prev_data.get("koact_date", "2026.06.16"),
                "holdings": prev_data["koact_holdings"]
            }
            print("KoAct 수집 실패 -> 이전 영업일 데이터 적용")
            
    timefolio_holdings = get_timefolio_holdings()
    if timefolio_holdings is None:
        if prev_data and "time_holdings" in prev_data:
            timefolio_holdings = {
                "date": prev_data.get("time_date", "2026.06.16"),
                "holdings": prev_data["time_holdings"]
            }
            print("Timefolio 수집 실패 -> 이전 영업일 데이터 적용")

    # 데이터 업데이트
    today_entry = {
        "fear_and_greed": fng_value,
        "sp500_price": sp500["price"],
        "sp500_change": sp500["change"],
        "nasdaq_price": nasdaq["price"],
        "nasdaq_change": nasdaq["change"],
        "vix_price": vix["price"],
        "vix_change": vix["change"],
        "dxy_price": dxy["price"],
        "dxy_change": dxy["change"]
    }
    
    # TOP 20 자산 데이터 추가
    if assets_top20:
        today_entry["assets_top20"] = assets_top20
        
    # AAII 데이터 추가
    if aaii_data:
        today_entry["aaii_bullish"] = aaii_data["bullish"]
        today_entry["aaii_neutral"] = aaii_data["neutral"]
        today_entry["aaii_bearish"] = aaii_data["bearish"]
        today_entry["aaii_date"] = aaii_data["date"]
        
    # Active ETF Holdings 추가
    if koact_holdings:
        today_entry["koact_date"] = koact_holdings["date"]
        today_entry["koact_holdings"] = koact_holdings["holdings"]
    if timefolio_holdings:
        today_entry["time_date"] = timefolio_holdings["date"]
        today_entry["time_holdings"] = timefolio_holdings["holdings"]
    
    dashboard_data[today_str] = today_entry
    
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
    print(f"  Nasdaq Composite: Price={nasdaq['price']}, Change={nasdaq['change']}%")
    print(f"  VIX: Price={vix['price']}, Change={vix['change']}%")
    print(f"  DXY: Price={dxy['price']}, Change={dxy['change']}%")
    if aaii_data:
        print(f"  AAII Sentiment: Bullish={aaii_data['bullish']}%, Neutral={aaii_data['neutral']}%, Bearish={aaii_data['bearish']}% (설문 마감: {aaii_data['date']})")

if __name__ == "__main__":
    main()
