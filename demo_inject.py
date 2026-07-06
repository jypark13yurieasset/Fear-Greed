import json
import os
from datetime import datetime, timedelta

def inject():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    idx_path = os.path.join(data_dir, "index_constituents.json")
    
    with open(idx_path, 'r') as f:
        data = json.load(f)
        
    stocks = data.get('stocks', [])
    if len(stocks) < 18: return
    
    today = datetime.now()
    log = []
    
    # 1-day streaks
    log.append({"date": (today - timedelta(days=7)).strftime("%Y-%m-%d"), "ticker": stocks[0]['ticker'], "name": stocks[0]['name'], "type": "golden", "streak": 1, "entry_price": stocks[0]['price'] * 0.95})
    log.append({"date": (today - timedelta(days=5)).strftime("%Y-%m-%d"), "ticker": stocks[1]['ticker'], "name": stocks[1]['name'], "type": "golden", "streak": 1, "entry_price": stocks[1]['price'] * 1.02})
    log.append({"date": (today - timedelta(days=6)).strftime("%Y-%m-%d"), "ticker": stocks[2]['ticker'], "name": stocks[2]['name'], "type": "dead", "streak": 1, "entry_price": stocks[2]['price'] * 1.05})
    log.append({"date": (today - timedelta(days=4)).strftime("%Y-%m-%d"), "ticker": stocks[3]['ticker'], "name": stocks[3]['name'], "type": "dead", "streak": 1, "entry_price": stocks[3]['price'] * 0.95})
    
    # 2-day streaks
    log.append({"date": (today - timedelta(days=8)).strftime("%Y-%m-%d"), "ticker": stocks[4]['ticker'], "name": stocks[4]['name'], "type": "golden", "streak": 2, "entry_price": stocks[4]['price'] * 0.92})
    log.append({"date": (today - timedelta(days=3)).strftime("%Y-%m-%d"), "ticker": stocks[5]['ticker'], "name": stocks[5]['name'], "type": "golden", "streak": 2, "entry_price": stocks[5]['price'] * 1.03})
    log.append({"date": (today - timedelta(days=7)).strftime("%Y-%m-%d"), "ticker": stocks[6]['ticker'], "name": stocks[6]['name'], "type": "dead", "streak": 2, "entry_price": stocks[6]['price'] * 1.08})
    log.append({"date": (today - timedelta(days=2)).strftime("%Y-%m-%d"), "ticker": stocks[7]['ticker'], "name": stocks[7]['name'], "type": "dead", "streak": 2, "entry_price": stocks[7]['price'] * 0.96})

    # 3-day streaks
    log.append({"date": (today - timedelta(days=9)).strftime("%Y-%m-%d"), "ticker": stocks[8]['ticker'], "name": stocks[8]['name'], "type": "golden", "streak": 3, "entry_price": stocks[8]['price'] * 0.90})
    log.append({"date": (today - timedelta(days=4)).strftime("%Y-%m-%d"), "ticker": stocks[9]['ticker'], "name": stocks[9]['name'], "type": "golden", "streak": 3, "entry_price": stocks[9]['price'] * 1.04})
    log.append({"date": (today - timedelta(days=8)).strftime("%Y-%m-%d"), "ticker": stocks[10]['ticker'], "name": stocks[10]['name'], "type": "dead", "streak": 3, "entry_price": stocks[10]['price'] * 1.10})
    log.append({"date": (today - timedelta(days=3)).strftime("%Y-%m-%d"), "ticker": stocks[11]['ticker'], "name": stocks[11]['name'], "type": "dead", "streak": 3, "entry_price": stocks[11]['price'] * 0.94})

    log_path = os.path.join(data_dir, "signal_log.json")
    js_path = os.path.join(data_dir, "signal_log.js")
    
    with open(log_path, 'w') as f:
        json.dump(log, f, indent=2)
        
    with open(js_path, 'w') as f:
        f.write(f"const SIGNAL_LOG_DATA = {json.dumps(log, indent=2)};\n")
        
    print("Injected mock signal logs for 1, 2, 3 day streaks.")

if __name__ == "__main__":
    inject()
