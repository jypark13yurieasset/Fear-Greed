import json
import os

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
log_path = os.path.join(data_dir, "signal_log.json")
idx_path = os.path.join(data_dir, "index_constituents.json")
js_path = os.path.join(data_dir, "signal_log.js")

if os.path.exists(log_path) and os.path.exists(idx_path):
    with open(idx_path, 'r') as f:
        idx_data = json.load(f)
    
    ticker_to_name = {s['ticker']: s['name'] for s in idx_data.get('stocks', [])}
    
    with open(log_path, 'r') as f:
        logs = json.load(f)
        
    for log in logs:
        if log['ticker'] in ticker_to_name:
            log['name'] = ticker_to_name[log['ticker']]
            
    with open(log_path, 'w') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)
        
    with open(js_path, 'w') as f:
        f.write(f"const SIGNAL_LOG_DATA = {json.dumps(logs, ensure_ascii=False, indent=2)};\n")
        
    print("Fixed names in signal_log!")
