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

def fetch_eps_trend(ticker):
    try:
        t = yf.Ticker(ticker)
        df = t.eps_trend
        if df is None or df.empty:
            return ticker, None
        
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
    
    results = {}
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_eps_trend, t): t for t in tickers}
        
        count = 0
        for future in as_completed(futures):
            ticker, data = future.result()
            count += 1
            if count % 50 == 0:
                print(f"Progress: {count}/{len(tickers)}")
                
            if data:
                results[ticker] = data

    print(f"Successfully fetched EPS trend for {len(results)} tickers.")
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    with open(OUTPUT_JS, 'w', encoding='utf-8') as f:
        f.write(f"window.eps_trend_data = {json.dumps(results, ensure_ascii=False)};")
        
    print("Done! Data saved.")

if __name__ == "__main__":
    main()
