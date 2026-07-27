import json
import os
import time
import update_earnings

def main():
    with open('data/index_constituents.json', 'r', encoding='utf-8') as f:
        constituents = json.load(f)
    stocks = constituents.get('stocks', [])
    tickers = [item.get('ticker') for item in stocks if item.get('ticker')]
    tickers = [t for t in tickers if t and not t.endswith('.KS') and not t.endswith('.KQ')]
    tickers = list(set(tickers))
    
    for t in ['MU', 'TSLA', 'AAPL', 'NVDA', 'MSFT', 'AMZN', 'META']:
        if t not in tickers:
            tickers.append(t)
            
    try:
        with open('data/eps_trend.json', 'r', encoding='utf-8') as f:
            results = json.load(f)
    except Exception:
        results = {}
        
    missing = [t for t in tickers if t not in results]
    print(f"Total missing tickers: {len(missing)}")
    if not missing:
        print("Nothing to fetch.")
        return
        
    count = 0
    for t in missing:
        count += 1
        print(f"[{count}/{len(missing)}] Fetching {t}...", flush=True)
        try:
            _, data = update_earnings.fetch_eps_trend(t)
            if data:
                results[t] = data
                print(f"  Success for {t}")
            else:
                print(f"  Failed for {t}")
        except Exception as e:
            print(f"  Error for {t}: {e}")
        time.sleep(0.5)  # prevent rate limit
        
    with open('data/eps_trend.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    with open('data/eps_trend.js', 'w', encoding='utf-8') as f:
        f.write(f"window.eps_trend_data = {json.dumps(results, ensure_ascii=False)};")
        
    print("Backfill complete.")

if __name__ == "__main__":
    main()
