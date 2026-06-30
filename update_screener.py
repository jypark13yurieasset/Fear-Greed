#!/usr/bin/env python3
"""
Fetch constituents of S&P 500, Nasdaq-100, and Dow Jones Industrial Average
from SlickCharts using curl_cffi, resolve sectors using Wikipedia as a fallback
database (with yfinance fallbacks and cross-checking), and download 1-year price history
from Yahoo Finance to compute momentum statistics.
"""
import pandas as pd
import requests
import json
import os
import sys
import time
import datetime
import statistics
import yfinance as yf
import urllib3
from bs4 import BeautifulSoup
from curl_cffi import requests as crequests
from dateutil.relativedelta import relativedelta
from concurrent.futures import ThreadPoolExecutor

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/'
}

# Check command line flags (e.g. python3 update_screener.py --force-check)
force_check = "--force-check" in sys.argv

# Load local sector database cache
sectors_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "screener_sectors.json")
sector_db = {}
if os.path.exists(sectors_cache_path):
    try:
        with open(sectors_cache_path, 'r', encoding='utf-8') as f:
            sector_db = json.load(f)
        print(f"✅ 로컬 섹터 DB 로드 완료 ({len(sector_db)}개 종목)")
    except Exception as e:
        print(f"⚠️ 로컬 섹터 DB 로딩 실패: {e}")

# --- 2. Fetch constituents from SlickCharts using curl_cffi ---
def fetch_slickcharts(url):
    print("\n" + "=" * 60)
    print(f"🔗 SlickCharts 수집 중: {url}")
    try:
        r = crequests.get(url, headers=headers, impersonate="chrome120", timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            table = soup.find('table')
            if not table:
                table = soup.find('table', {'class': 'table'})
            if table:
                rows = table.find_all('tr')[1:] # skip header
                constituents = []
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        company = cols[1].text.strip()
                        symbol = cols[2].text.strip()
                        constituents.append({
                            'ticker': symbol,
                            'name': company
                        })
                print(f"   성공: {len(constituents)}개 종목 수집")
                return constituents
            else:
                print("   ❌ 테이블을 찾지 못했습니다.")
        else:
            print(f"   ❌ HTTP 에러: {r.status_code}")
    except Exception as e:
        print(f"   ❌ SlickCharts 수집 에러: {e}")
    return []

sp500_list = fetch_slickcharts("https://www.slickcharts.com/sp500")
ndx_list = fetch_slickcharts("https://www.slickcharts.com/nasdaq100")
dow_list = fetch_slickcharts("https://www.slickcharts.com/dowjones")

# Fallback to local cache if scraping fails (e.g., due to IP blocks in GitHub Actions)
existing_sp500 = []
existing_ndx = []
existing_dow = []

existing_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "index_constituents.json")
if os.path.exists(existing_json_path):
    try:
        with open(existing_json_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            for stock in existing_data.get('stocks', []):
                ticker = stock.get('ticker')
                name = stock.get('name')
                if stock.get('sp500'):
                    existing_sp500.append({'ticker': ticker, 'name': name})
                if stock.get('nasdaq100'):
                    existing_ndx.append({'ticker': ticker, 'name': name})
                if stock.get('dowjones'):
                    existing_dow.append({'ticker': ticker, 'name': name})
        print(f"   [캐시] 기존 저장된 구성종목 로드 완료: S&P 500={len(existing_sp500)}개, NDX={len(existing_ndx)}개, Dow={len(existing_dow)}개")
    except Exception as e:
        print(f"   ⚠️ 기존 구성종목 캐시 로드 에러: {e}")

if not sp500_list and existing_sp500:
    print("   ⚠️ S&P 500 SlickCharts 수집 실패. 기존 캐시 데이터를 복원합니다.")
    sp500_list = existing_sp500
if not ndx_list and existing_ndx:
    print("   ⚠️ Nasdaq-100 SlickCharts 수집 실패. 기존 캐시 데이터를 복원합니다.")
    ndx_list = existing_ndx
if not dow_list and existing_dow:
    print("   ⚠️ Dow Jones SlickCharts 수집 실패. 기존 캐시 데이터를 복원합니다.")
    dow_list = existing_dow

# --- 3. Sector Resolution with Cross-Checking ---
print("\n" + "=" * 60)
print("📋 구성종목 데이터 병합 및 섹터 교차 검증...")

YAHOO_SECTOR_MAP = {
    'Technology': 'Information Technology',
    'Healthcare': 'Health Care',
    'Consumer Cyclical': 'Consumer Discretionary',
    'Financial Services': 'Financials',
    'Consumer Defensive': 'Consumer Staples',
    'Basic Materials': 'Materials'
}

def clean_sector(s):
    return YAHOO_SECTOR_MAP.get(s, s)

def fetch_yahoo_sector_info(ticker):
    yf_t = ticker
    if not ticker.endswith('.KS'):
        yf_t = ticker.replace('.', '-')
    try:
        t_obj = yf.Ticker(yf_t)
        info = t_obj.info
        sector = clean_sector(info.get('sector', ''))
        sub_industry = info.get('industry', '')
        name = info.get('longName', info.get('shortName', ''))
        return sector, sub_industry, name
    except Exception as e:
        print(f"   ⚠️ 야후 파이낸스 조회 에러 ({ticker}): {e}")
    return '', '', ''

def get_sector_info(ticker, force=False):
    # If not forcing check and already cached in db, use cache
    if not force and ticker in sector_db:
        cached = sector_db[ticker]
        return cached.get('sector', ''), cached.get('sub_industry', ''), cached.get('name', ticker)
        
    # Fetch from Yahoo Finance API directly
    print(f"   🔍 야후 파이낸스 섹터 조회 중: {ticker}")
    yf_sec, yf_sub, yf_nm = fetch_yahoo_sector_info(ticker)
    
    # Override SpaceX details specifically
    if ticker == 'SPCX':
        yf_sec = 'Industrials' # 11 GICS sector standard
        yf_sub = 'Aerospace & Defense'
        yf_nm = 'SpaceX'
            
    # Save/Update in Local Sector Cache
    sector_db[ticker] = {
        'sector': yf_sec,
        'sub_industry': yf_sub,
        'name': yf_nm or ticker
    }
    
    # Save cache update to disk
    try:
        with open(sectors_cache_path, 'w', encoding='utf-8') as f:
            json.dump(sector_db, f, ensure_ascii=False, indent=2)
    except:
        pass
        
    return sector_db[ticker]['sector'], sector_db[ticker]['sub_industry'], sector_db[ticker]['name']

stock_map = {}

# S&P 500
for s in sp500_list:
    t = s['ticker']
    sector, sub_industry, final_name = get_sector_info(t, force=force_check)
    stock_map[t] = {
        'ticker': t,
        'name': final_name or s['name'],
        'sector': sector,
        'sub_industry': sub_industry,
        'sp500': True,
        'nasdaq100': False,
        'dowjones': False,
        'is_watchlist': False
    }
    if force_check:
        time.sleep(0.15) # Delay if force checking to prevent 429

# Nasdaq-100
for s in ndx_list:
    t = s['ticker']
    if t in stock_map:
        stock_map[t]['nasdaq100'] = True
    else:
        sector, sub_industry, final_name = get_sector_info(t, force=force_check)
        stock_map[t] = {
            'ticker': t,
            'name': final_name or s['name'],
            'sector': sector,
            'sub_industry': sub_industry,
            'sp500': False,
            'nasdaq100': True,
            'dowjones': False,
            'is_watchlist': False
        }
        if force_check:
            time.sleep(0.15)

# Dow Jones
for s in dow_list:
    t = s['ticker']
    if t in stock_map:
        stock_map[t]['dowjones'] = True
        if not stock_map[t]['sector']:
            sector, sub_industry, _ = get_sector_info(t, force=force_check)
            if sector:
                stock_map[t]['sector'] = sector
                stock_map[t]['sub_industry'] = sub_industry
                if force_check:
                    time.sleep(0.15)
    else:
        sector, sub_industry, final_name = get_sector_info(t, force=force_check)
        stock_map[t] = {
            'ticker': t,
            'name': final_name or s['name'],
            'sector': sector,
            'sub_industry': sub_industry,
            'sp500': False,
            'nasdaq100': False,
            'dowjones': True,
            'is_watchlist': False
        }
        if force_check:
            time.sleep(0.15)

# Inject Watchlist Stocks
# 5 Watchlist: SpaceX (SPCX), Tesla, Samsung, SK Hynix, Micron
watchlist_tickers = {
    'TSLA': 'Tesla, Inc.',
    'MU': 'Micron Technology, Inc.',
    '005930.KS': 'Samsung Electronics Co., Ltd.',
    '000660.KS': 'SK Hynix Inc.',
    'SPCX': 'SpaceX'
}

for wt, wname in watchlist_tickers.items():
    if wt in stock_map:
        stock_map[wt]['is_watchlist'] = True
        if wt == 'SPCX':
            stock_map[wt]['name'] = wname
    else:
        sector, sub_industry, _ = get_sector_info(wt, force=force_check)
        stock_map[wt] = {
            'ticker': wt,
            'name': wname,
            'sector': sector or ('Industrials' if wt == 'SPCX' else 'Information Technology'),
            'sub_industry': sub_industry or ('Space Exploration' if wt == 'SPCX' else 'Semiconductors'),
            'sp500': False,
            'nasdaq100': False,
            'dowjones': False,
            'is_watchlist': True
        }
        if force_check:
            time.sleep(0.15)

print(f"   총 고유 구성종목 수 (관심종목 포함): {len(stock_map)}개")

# Save Local Sector Database cache one last time
try:
    with open(sectors_cache_path, 'w', encoding='utf-8') as f:
        json.dump(sector_db, f, ensure_ascii=False, indent=2)
    print(f"💾 로컬 섹터 DB 업데이트 저장 완료 ({len(sector_db)}개 종목)")
except Exception as e:
    print(f"⚠️ 로컬 섹터 DB 저장 실패: {e}")

# --- 4. Bulk Download Price History using yfinance ---
print("\n" + "=" * 60)
print("📈 야후 파이낸스(yfinance)로부터 가격 이력 벌크 다운로드 중...")

# Build list of tickers to fetch
tickers_to_fetch = []
ticker_mapping = {} # yfinance_ticker -> original_ticker

for t in stock_map.keys():
    yf_t = t
    if not t.endswith('.KS'):
        yf_t = t.replace('.', '-')
    tickers_to_fetch.append(yf_t)
    ticker_mapping[yf_t] = t

# Fetch in batches of 100
batch_size = 100
all_data = {}
batches = [tickers_to_fetch[i:i + batch_size] for i in range(0, len(tickers_to_fetch), batch_size)]

for idx, batch in enumerate(batches):
    print(f"   다운로드 중 batch {idx+1}/{len(batches)} ({len(batch)}개 종목)...")
    try:
        df = yf.download(batch, period="2y", interval="1d", auto_adjust=False, group_by="ticker", progress=False)
        
        if isinstance(df.columns, pd.MultiIndex):
            for yf_ticker in batch:
                orig_ticker = ticker_mapping[yf_ticker]
                if yf_ticker in df.columns.levels[0]:
                    ticker_df = df[yf_ticker]
                    series = ticker_df[['Close', 'Volume']].dropna()
                    if not series.empty:
                        if series.index.tz is not None:
                            series.index = series.index.tz_localize(None)
                        all_data[orig_ticker] = series
        else:
            yf_ticker = batch[0]
            orig_ticker = ticker_mapping[yf_ticker]
            series = df[['Close', 'Volume']].dropna()
            if not series.empty:
                if series.index.tz is not None:
                    series.index = series.index.tz_localize(None)
                all_data[orig_ticker] = series
    except Exception as e:
        print(f"   ❌ Batch {idx+1} 에러: {e}")

print(f"   다운로드 완료: {len(all_data)}개 종목 성공")

# --- 4.5 Fetch trailingPE and forwardPE ---
print("\n" + "=" * 60)
print("🔍 Finviz(우선) 및 야후 파이낸스(대체)로부터 PER, Forward PER 정보 조회 중 (병렬 처리)...")
info_data = {}
def fetch_info(item):
    yf_t, orig_t = item
    pe, fpe, mcap, target_price = None, None, None, None
    
    # Try Finviz first (only for US stocks)
    if not orig_t.endswith('.KS') and not orig_t.endswith('.KQ'):
        try:
            finviz_t = orig_t.replace('-', '.')
            url = f"https://finviz.com/quote.ashx?t={finviz_t}"
            r = crequests.get(url, headers=headers, impersonate="chrome110", timeout=5)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                tds = soup.find_all('td')
                for i, td in enumerate(tds):
                    if td.text == 'P/E':
                        pe_val = tds[i+1].text
                        if pe_val != '-':
                            pe = float(pe_val)
                    if td.text == 'Forward P/E':
                        fpe_val = tds[i+1].text
                        if fpe_val != '-':
                            fpe = float(fpe_val)
                    if td.text == 'Market Cap':
                        mcap_val = tds[i+1].text
                        if mcap_val != '-':
                            mcap = mcap_val
                    if td.text == 'Target Price':
                        tp_val = tds[i+1].text
                        if tp_val != '-':
                            try:
                                target_price = float(tp_val)
                            except Exception:
                                pass
        except Exception:
            pass
            
    # Try Naver Finance for Korean stocks
    elif orig_t.endswith('.KS') or orig_t.endswith('.KQ'):
        try:
            import requests as req
            code = orig_t.split('.')[0]
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            r = req.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                per_elem = soup.select_one('#_per')
                if per_elem:
                    try: pe = float(per_elem.text.replace(',', ''))
                    except Exception: pass
                fwd_elem = soup.select_one('#_cns_per')
                if fwd_elem:
                    try: fpe = float(fwd_elem.text.replace(',', ''))
                    except Exception: pass
                for th in soup.find_all('th'):
                    if '목표주가' in th.text:
                        td = th.find_next_sibling('td')
                        if td:
                            ems = td.find_all('em')
                            if len(ems) >= 2:
                                try: target_price = float(ems[1].text.replace(',', ''))
                                except Exception: pass
                mcap_elem = soup.select_one('#_market_sum')
                if mcap_elem:
                    mcap_text = mcap_elem.text.strip().replace('\t', '').replace('\n', '')
                    if mcap_text:
                        mcap = mcap_text + "원"
        except Exception:
            pass
            
    # Fallback to Yahoo Finance if Finviz failed or missing data
    if pe is None or fpe is None:
        try:
            info = yf.Ticker(yf_t).info
            if pe is None:
                pe = info.get("trailingPE")
            if fpe is None:
                fpe = info.get("forwardPE")
            if mcap is None:
                raw_mcap = info.get("marketCap")
                if raw_mcap:
                    if raw_mcap >= 1e9:
                        mcap = f"{raw_mcap/1e9:.2f}B"
                    elif raw_mcap >= 1e6:
                        mcap = f"{raw_mcap/1e6:.2f}M"
                    else:
                        mcap = str(raw_mcap)
            if target_price is None:
                target_price = info.get("targetMeanPrice")
        except Exception:
            pass

    return orig_t, pe, fpe, mcap, target_price

with ThreadPoolExecutor(max_workers=10) as executor:
    results_info = list(executor.map(fetch_info, ticker_mapping.items()))
for orig_t, pe, fpe, mcap, target_price in results_info:
    info_data[orig_t] = {"trailingPE": pe, "forwardPE": fpe, "marketCap": mcap, "targetPrice": target_price}

# --- Helper functions for technical indicators ---

def calc_ema(closes, period):
    """Exponential Moving Average using standard multiplier 2/(period+1)."""
    if len(closes) < period:
        return None
    k = 2.0 / (period + 1)
    ema = sum(closes[:period]) / period  # seed with SMA
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
    return ema

def get_ema_array(data, period):
    if len(data) < period:
        return [None]*len(data)
    emas = []
    k = 2.0 / (period + 1)
    ema = sum(data[:period]) / period
    emas.append(ema)
    for price in data[period:]:
        ema = price * k + ema * (1 - k)
        emas.append(ema)
    return [None]*(period-1) + emas

def calc_sma(closes, period):
    """Simple Moving Average."""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period

def calc_rsi(closes, period=14):
    """Wilder's RSI using smoothed moving averages."""
    if len(closes) < period + 1:
        return None
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(c, 0) for c in changes]
    losses = [abs(min(c, 0)) for c in changes]
    # Initial average gain/loss (SMA seed)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    # Wilder smoothing for remaining periods
    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def calc_macd_state(closes):
    """Returns MACD state: 4=🚀Strong Bull, 3=📈Bull Turn, 2=📉Bear Turn, 1=❄️Strong Bear"""
    if len(closes) < 35:
        return None
        
    ema12 = get_ema_array(closes, 12)
    ema26 = get_ema_array(closes, 26)
    
    macd_line = []
    for e12, e26 in zip(ema12, ema26):
        if e12 is not None and e26 is not None:
            macd_line.append(e12 - e26)
            
    if len(macd_line) < 9:
        return None
        
    signal = calc_ema(macd_line, 9)
    current_macd = macd_line[-1]
    histogram = current_macd - signal
    
    if current_macd > 0 and histogram > 0:
        return 4
    elif current_macd <= 0 and histogram > 0:
        return 3
    elif current_macd > 0 and histogram <= 0:
        return 2
    else:
        return 1

# --- 5. Calculate Momentum Metrics ---
print("\n" + "=" * 60)
print("🧮 모멘텀 지표 연산 중...")
stocks_output = []

# Base date in KST matching script execution date (Google Finance baseline)
# If weekend (Saturday/Sunday), adjust to the previous Friday to capture Friday's final market close
now_kst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
if now_kst.weekday() == 5:    # Saturday
    now_kst = now_kst - datetime.timedelta(days=1)
elif now_kst.weekday() == 6:  # Sunday
    now_kst = now_kst - datetime.timedelta(days=2)
run_date_str = now_kst.strftime("%Y-%m-%d")
baseline_date = pd.Timestamp(run_date_str)

for t, s in stock_map.items():
    series = all_data.get(t)
    
    price = None
    pct_1d = None
    pct_1w = None
    pct_1m = None
    pct_3m = None
    pct_1y = None
    dist_high = None
    dist_low = None
    dist_ma50 = None
    dist_ma200 = None
    rel_vol = None
    # New technical indicators
    ema_signal = None    # 1=below both, 2=between, 3=above both
    macd_state = None    # 1=Strong Bear, 2=Bear Turn, 3=Bull Turn, 4=Strong Bull
    dist_sma20 = None    # (price - SMA20) / SMA20 * 100
    rsi14 = None         # Wilder's RSI-14
    
    if series is not None and not series.empty:
        closes = series['Close'].tolist()
        volumes = series['Volume'].tolist()
        price = closes[-1]
        latest_trading_date = series.index[-1]
        today_date = baseline_date
        
        # Helper to get return based on the Nth trading day back
        def calc_pct_by_trading_days(n):
            """Return % change vs the Nth trading day before the latest close."""
            idx = -(n + 1)  # e.g. n=5 → iloc[-6]
            if len(series) >= (n + 1):
                past_price = series['Close'].iloc[idx]
                if past_price and past_price > 0:
                    return (price - past_price) / past_price * 100
            return None

        # Helper to get return at specific calendar date (for month/year periods)
        def calc_pct_change(target_date):
            ts = pd.Timestamp(target_date)
            asof_date = series.index.asof(ts)
            if pd.notna(asof_date):
                if asof_date < latest_trading_date:
                    past_price = series['Close'].loc[asof_date]
                    if past_price and past_price > 0:
                        return (price - past_price) / past_price * 100
            return None

        # 1D Change (1 trading day back)
        pct_1d = calc_pct_by_trading_days(1)
            
        # 5D Change (5 trading days back)
        pct_1w = calc_pct_by_trading_days(5)
            
        # 1M Change (1 calendar month from baseline date)
        pct_1m = calc_pct_change(today_date - relativedelta(months=1))
            
        # 3M Change (3 calendar months from baseline date)
        pct_3m = calc_pct_change(today_date - relativedelta(months=3))
            
        # 6M Change (6 calendar months from baseline date)
        pct_6m = calc_pct_change(today_date - relativedelta(months=6))
            
        # YTD Change (from the last trading day of previous year of baseline date)
        ytd_target_date = datetime.date(today_date.year - 1, 12, 31)
        pct_ytd = calc_pct_change(ytd_target_date)
            
        # 1Y Change (1 calendar year from baseline date)
        pct_1y = calc_pct_change(today_date - relativedelta(years=1))
            
        # 52W High / Low (based on the last 252 trading days to represent 1 year)
        closes_1y = closes[-252:] if len(closes) >= 252 else closes
        high_52w = max(closes_1y)
        low_52w = min(closes_1y)
        if high_52w > 0:
            dist_high = (price - high_52w) / high_52w * 100
        if low_52w > 0:
            dist_low = (price - low_52w) / low_52w * 100
            
        # 50MA and 200MA
        ma50 = calc_sma(closes, 50)
        if ma50 and ma50 > 0:
            dist_ma50 = (price - ma50) / ma50 * 100
        ma200 = calc_sma(closes, 200)
        if ma200 and ma200 > 0:
            dist_ma200 = (price - ma200) / ma200 * 100
        
        # --- New Technical Indicators ---
        
        # EMA8 & EMA21 → 4-tier State (MACD-style)
        ema8 = calc_ema(closes, 8)
        ema21 = calc_ema(closes, 21)
        if ema8 is not None and ema21 is not None:
            trend_bull = ema8 > ema21
            momentum_bull = price > ema8
            
            if trend_bull and momentum_bull:
                ema_signal = 4   # 🚀 강력 상승
            elif not trend_bull and momentum_bull:
                ema_signal = 3   # 📈 상승 반전
            elif trend_bull and not momentum_bull:
                ema_signal = 2   # 📉 하락 반전
            else:
                ema_signal = 1   # ❄️ 강력 하락
        
        # SMA20 이격도
        sma20 = calc_sma(closes, 20)
        if sma20 and sma20 > 0:
            dist_sma20 = (price - sma20) / sma20 * 100
        
        # RSI-14
        rsi14 = calc_rsi(closes, 14)
        rsi14_w = None
        rsi14_m = None
        if series is not None and len(series) >= 15:
            try:
                closes_w = series['Close'].resample("W").last().dropna().tolist()
                closes_m = series['Close'].resample("ME").last().dropna().tolist()
                rsi14_w = calc_rsi(closes_w, 14)
                rsi14_m = calc_rsi(closes_m, 14)
            except Exception:
                pass
                
        # MACD
        macd_state = calc_macd_state(closes)
        
        # Danger Dead Cross (MACD Histogram < 0 AND EMA 8 crossed below EMA 21 in last 2 days)
        is_danger_dead_cross = False
        if macd_state in [1, 2] and ema8 is not None and ema21 is not None and ema8 < ema21: # Histogram < 0 AND Currently in Dead Cross state
            ema8_arr = get_ema_array(closes, 8)
            ema21_arr = get_ema_array(closes, 21)
            if len(ema8_arr) >= 3:
                for i in range(-2, 0):
                    if ema8_arr[i] is not None and ema21_arr[i] is not None and ema8_arr[i-1] is not None and ema21_arr[i-1] is not None:
                        if ema8_arr[i] < ema21_arr[i] and ema8_arr[i-1] >= ema21_arr[i-1]:
                            is_danger_dead_cross = True
                            break
                            
        # Golden Cross Opportunity (MACD Histogram > 0 AND EMA 8 crossed above EMA 21 in last 2 days)
        is_golden_cross_opportunity = False
        if macd_state in [3, 4] and ema8 is not None and ema21 is not None and ema8 > ema21: # Histogram > 0 AND Currently in Golden Cross state
            ema8_arr = get_ema_array(closes, 8)
            ema21_arr = get_ema_array(closes, 21)
            if len(ema8_arr) >= 3:
                for i in range(-2, 0):
                    if ema8_arr[i] is not None and ema21_arr[i] is not None and ema8_arr[i-1] is not None and ema21_arr[i-1] is not None:
                        if ema8_arr[i] > ema21_arr[i] and ema8_arr[i-1] <= ema21_arr[i-1]:
                            is_golden_cross_opportunity = True
                            break

        # Relative Volume (3-month average, approx 63 trading days)
        if len(volumes) >= 63:
            avg_vol_3m = sum(volumes[-63:]) / 63
        elif len(volumes) > 0:
            avg_vol_3m = sum(volumes) / len(volumes)
        else:
            avg_vol_3m = 0
            
        current_vol = volumes[-1] if len(volumes) > 0 else 0
        if avg_vol_3m > 0:
            rel_vol = current_vol / avg_vol_3m
        else:
            rel_vol = None

    def rnd(val):
        return round(val, 2) if val is not None else None

    stocks_output.append({
        'ticker': s['ticker'],
        'name': s['name'],
        'sector': s['sector'],
        'sub_industry': s['sub_industry'],
        'sp500': s['sp500'],
        'nasdaq100': s['nasdaq100'],
        'dowjones': s['dowjones'],
        'is_watchlist': s['is_watchlist'],
        'is_private': False,
        'price': rnd(price),
        'pct_1d': rnd(pct_1d),
        'pct_1w': rnd(pct_1w),
        'pct_1m': rnd(pct_1m),
        'pct_3m': rnd(pct_3m),
        'pct_6m': rnd(pct_6m),
        'pct_ytd': rnd(pct_ytd),
        'pct_1y': rnd(pct_1y),
        'trailingPE': rnd(info_data.get(t, {}).get("trailingPE")),
        'forwardPE': rnd(info_data.get(t, {}).get("forwardPE")),
        'ema_signal': ema_signal,       # int 1/2/3 or null
        'macd_state': macd_state,       # int 1/2/3/4 or null
        'is_danger_dead_cross': is_danger_dead_cross,
        'is_golden_cross_opportunity': is_golden_cross_opportunity,
        'dist_sma20': rnd(dist_sma20),  # SMA20 이격도 (%)
        'rsi14': rnd(rsi14),            # RSI-14 수치
        'rsi14_w': rnd(rsi14_w),
        'rsi14_m': rnd(rsi14_m),
        'rel_vol': rnd(rel_vol),
        'dist_high': rnd(dist_high),
        'dist_low': rnd(dist_low),
        'dist_ma50': rnd(dist_ma50),
        'dist_ma200': rnd(dist_ma200),
        'marketCap': info_data.get(t, {}).get("marketCap", "-"),
        'targetPrice': rnd(info_data.get(t, {}).get("targetPrice"))
    })

results = {
    'date': run_date_str,
    'stocks': stocks_output
}

# --- Safety Check: Ensure we don't save a truncated dataset ---
if len(stocks_output) < 400:
    print(f"\n❌ 에러: 생성할 구성종목 개수가 {len(stocks_output)}개로 너무 적습니다 (기준: 400개 이상).")
    print("데이터 정합성 오류로 판단되어 저장 작업을 중단하고 종료합니다.")
    sys.exit(1)

# --- 6. Save Output ---
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(output_dir, exist_ok=True)

# Save JSON
json_path = os.path.join(output_dir, "index_constituents.json")
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n✅ JSON 데이터가 {json_path}에 저장되었습니다.")

# Save JS (Global Variable)
js_path = os.path.join(output_dir, "index_constituents.js")
with open(js_path, 'w', encoding='utf-8') as f:
    f.write(f"const INDEX_DATA = {json.dumps(results, ensure_ascii=False, indent=2)};\n")
print(f"✅ JS 데이터가 {js_path}에 저장되었습니다.")
