import json
import os
from datetime import datetime, timedelta

def inject():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    idx_path = os.path.join(data_dir, "index_constituents.json")
    
    with open(idx_path, 'r') as f:
        data = json.load(f)
        
    stocks = data.get('stocks', [])
    
    # Let's pick a few stocks
    # 0, 1, 2 for Golden, 3, 4, 5 for Dead
    if len(stocks) < 6: return
    
    today = datetime.now()
    
    # Format: {"date": "YYYY-MM-DD", "ticker": "...", "name": "...", "type": "golden"/"dead", "entry_price": 100}
    log = [
        # Win (Current price > Entry)
        {"date": (today - timedelta(days=7)).strftime("%Y-%m-%d"), "ticker": stocks[0]['ticker'], "name": stocks[0]['name'], "type": "golden", "entry_price": stocks[0]['price'] * 0.95},
        # Loss (Current price < Entry)
        {"date": (today - timedelta(days=5)).strftime("%Y-%m-%d"), "ticker": stocks[1]['ticker'], "name": stocks[1]['name'], "type": "golden", "entry_price": stocks[1]['price'] * 1.02},
        # Win (Current price > Entry)
        {"date": (today - timedelta(days=2)).strftime("%Y-%m-%d"), "ticker": stocks[2]['ticker'], "name": stocks[2]['name'], "type": "golden", "entry_price": stocks[2]['price'] * 0.98},
        
        # Dead Win (Current price < Entry)
        {"date": (today - timedelta(days=6)).strftime("%Y-%m-%d"), "ticker": stocks[3]['ticker'], "name": stocks[3]['name'], "type": "dead", "entry_price": stocks[3]['price'] * 1.05},
        # Dead Loss (Current price > Entry)
        {"date": (today - timedelta(days=4)).strftime("%Y-%m-%d"), "ticker": stocks[4]['ticker'], "name": stocks[4]['name'], "type": "dead", "entry_price": stocks[4]['price'] * 0.95},
        # Dead Win (Current price < Entry)
        {"date": (today - timedelta(days=1)).strftime("%Y-%m-%d"), "ticker": stocks[5]['ticker'], "name": stocks[5]['name'], "type": "dead", "entry_price": stocks[5]['price'] * 1.01},
    ]
    
    log_path = os.path.join(data_dir, "signal_log.json")
    js_path = os.path.join(data_dir, "signal_log.js")
    
    with open(log_path, 'w') as f:
        json.dump(log, f, indent=2)
        
    with open(js_path, 'w') as f:
        f.write(f"const SIGNAL_LOG_DATA = {json.dumps(log, indent=2)};\n")
        
    print("Injected mock signal logs for testing.")

if __name__ == "__main__":
    inject()
