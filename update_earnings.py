import json
import os
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
import pandas as pd

# Suppress urllib3 warnings
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL')

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
INPUT_JSON = os.path.join(DATA_DIR, 'index_constituents.json')
OUTPUT_JSON = os.path.join(DATA_DIR, 'eps_trend.json')
OUTPUT_JS = os.path.join(DATA_DIR, 'eps_trend.js')
INFO_CACHE_JSON = os.path.join(DATA_DIR, 'yf_info_cache.json')

yf_info_cache = {}
try:
    if os.path.exists(INFO_CACHE_JSON):
        with open(INFO_CACHE_JSON, 'r', encoding='utf-8') as f:
            yf_info_cache = json.load(f)
        print(f"Loaded {len(yf_info_cache)} info records from cache.")
except Exception:
    pass

def _end_date_to_label(end_date_str, is_yearly=False):
    """Convert '2026-09-30' to 'Sep 2026' for quarters, or '2026' for years."""
    try:
        from datetime import datetime
        dt = datetime.strptime(end_date_str, '%Y-%m-%d')
        if is_yearly:
            return str(dt.year)
        return dt.strftime('%b %Y')  # e.g. 'Sep 2026'
    except Exception:
        return None

def fetch_eps_trend(ticker):
    try:
        t = yf.Ticker(ticker)
        df = t.eps_trend
        if df is None or df.empty:
            return ticker, None
        
        # Extract endDate labels from raw earnings trend data
        labels = {}
        try:
            analysis = t._analysis
            analysis._fetch_earnings_trend()
            raw_trend = analysis._earnings_trend
            if raw_trend:
                for item in raw_trend:
                    period = item.get('period')
                    end_date = item.get('endDate')
                    if period and end_date:
                        is_yearly = period in ['0y', '+1y']
                        label = _end_date_to_label(end_date, is_yearly)
                        if label:
                            labels[period] = label
        except Exception:
            pass
        
        # We want to extract '0y', '+1y', '0q', and '+1q' periods
        data = {}
        for period in ['0q', '+1q', '0y', '+1y']:
            if period in df.index:
                row = df.loc[period]
                data[period] = [
                    float(row['90daysAgo']) if pd.notna(row['90daysAgo']) else None,
                    float(row['60daysAgo']) if pd.notna(row['60daysAgo']) else None,
                    float(row['30daysAgo']) if pd.notna(row['30daysAgo']) else None,
                    float(row['7daysAgo']) if pd.notna(row['7daysAgo']) else None,
                    float(row['current']) if pd.notna(row['current']) else None
                ]
        
        if not data:
            return ticker, None
        
        # Attach labels if available
        if labels:
            data['_labels'] = labels
            
        # Extract financial highlights
        financial_highlights_keys = [
            'nextFiscalYearEnd', 'mostRecentQuarter',
            'profitMargins', 'operatingMargins',
            'returnOnAssets', 'returnOnEquity', 'totalRevenue', 'revenuePerShare',
            'revenueGrowth', 'grossProfits', 'ebitda', 'netIncomeToCommon',
            'trailingEps', 'forwardEps', 'earningsGrowth', 'totalCash',
            'totalCashPerShare', 'totalDebt', 'debtToEquity', 'currentRatio',
            'bookValue', 'operatingCashflow', 'freeCashflow'
        ]
        
        try:
            info = yf_info_cache.get(ticker) or t.info
            if info:
                highlights = {}
                for k in financial_highlights_keys:
                    val = info.get(k)
                    if pd.notna(val):
                        highlights[k] = val
                if highlights:
                    data['_financial_highlights'] = highlights
                    
                # Extract valuation measures (current from info)
                valuation_keys = [
                    'marketCap', 'enterpriseValue', 'trailingPE', 'forwardPE',
                    'pegRatio', 'priceToSalesTrailing12Months', 'priceToBook',
                    'enterpriseToRevenue', 'enterpriseToEbitda'
                ]
                valuation = {}
                for k in valuation_keys:
                    val = info.get(k)
                    if pd.notna(val):
                        valuation[k] = val
                if valuation:
                    data['_valuation_measures'] = valuation
        except Exception:
            pass
        
        except Exception:
            pass
            
        return ticker, data
    except Exception as e:
        return ticker, None

def main():
    print("Loading constituents...")
    if not os.path.exists(INPUT_JSON):
        print(f"File not found: {INPUT_JSON}")
        return
        
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        constituents = json.load(f)
        
    stocks = constituents.get('stocks', [])
    tickers = [item.get('ticker') for item in stocks if item.get('ticker')]
    # Filter out empty or weird tickers
    tickers = [t for t in tickers if t and not t.endswith('.KS') and not t.endswith('.KQ')]
    # Remove duplicates
    tickers = list(set(tickers))
    
    # Also add standard test ones just in case
    for t in ['MU', 'TSLA', 'AAPL', 'NVDA', 'MSFT', 'AMZN', 'META']:
        if t not in tickers:
            tickers.append(t)
            
    print(f"Total valid US tickers to fetch: {len(tickers)}")
    
    # Load existing results to prevent wiping out data on rate limit failures
    results = {}
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
                results = json.load(f)
            print(f"Loaded {len(results)} existing tickers from cache.")
        except Exception:
            pass
            
    # Find which ones really need to be fetched (or we can just fetch all and overwrite)
    # To be safe against rate limits, we will still fetch all, but if it fails, the old data remains in `results`
    
    # Helper to fetch a batch
    def fetch_batch(ticker_list, workers=1):
        import time
        batch_results = {}
        failed = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Add a small delay between submitting tasks to avoid rate limits
            futures = {}
            for t in ticker_list:
                futures[executor.submit(fetch_eps_trend, t)] = t
                time.sleep(0.5) # Prevent Yahoo Finance rate limit (429/404)
            
            count = 0
            for future in as_completed(futures):
                t_str, data = future.result()
                count += 1
                if count % 50 == 0:
                    print(f"Progress: {count}/{len(ticker_list)}")
                if data:
                    batch_results[t_str] = data
                else:
                    failed.append(t_str)
        return batch_results, failed

    # First pass
    print("Starting first pass...")
    batch_data, failed_tickers = fetch_batch(tickers, workers=1)
    results.update(batch_data)
    
    # Retry logic (up to 2 more times)
    retries = 2
    while retries > 0 and failed_tickers:
        print(f"\nRate limit or failed to fetch {len(failed_tickers)} tickers. Retrying in 5 seconds...")
        import time
        time.sleep(5)
        print(f"Retry {3 - retries}: Fetching {len(failed_tickers)} failed tickers...")
        batch_data, failed_tickers = fetch_batch(failed_tickers, workers=1)
        results.update(batch_data)
        retries -= 1
        
    if failed_tickers:
        print(f"\nWARNING: Could not fetch {len(failed_tickers)} tickers even after retries.")
        print(f"Failed tickers: {', '.join(failed_tickers)}")
        print("These tickers will display '데이터 없음' on the website. Please retry them later.")

    print(f"\nSuccessfully populated EPS trend for {len(results)} tickers.")
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    with open(OUTPUT_JS, 'w', encoding='utf-8') as f:
        f.write(f"window.eps_trend_data = {json.dumps(results, ensure_ascii=False)};")
        
    print("Done! Data saved.")

if __name__ == "__main__":
    main()
