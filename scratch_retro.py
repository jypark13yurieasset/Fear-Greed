import json
import os
import yfinance as yf
from update_screener import calc_macd_state, get_ema_array

DATA_DIR = "/Users/junyounggarypark/Documents/GitHub/Fear-Greed/data"
signals_path = os.path.join(DATA_DIR, "screener_signals.json")
json_path = os.path.join(DATA_DIR, "index_constituents.json")

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

golden = [s['ticker'] for s in data['stocks'] if s.get('is_golden_cross_opportunity')]
dead = [s['ticker'] for s in data['stocks'] if s.get('is_danger_dead_cross')]

golden_yesterday = []
dead_yesterday = []

# Fetch last 30 days of data for these specific stocks sequentially
for t in golden:
    try:
        hist = yf.download(t, period="40d", interval="1d", progress=False)
        if not hist.empty:
            c = hist['Close'].dropna().tolist()[:-1] # Remove today
            if len(c) > 30:
                m = calc_macd_state(c)
                e8 = get_ema_array(c, 8)
                e21 = get_ema_array(c, 21)
                if m in [3, 4] and e8[-1] is not None and e21[-1] is not None and e8[-1] > e21[-1]:
                    if (e8[-1] > e21[-1] and e8[-2] <= e21[-2]) or (e8[-2] > e21[-2] and e8[-3] <= e21[-3]):
                        golden_yesterday.append(t)
    except Exception as e:
        pass
                        
for t in dead:
    try:
        hist = yf.download(t, period="40d", interval="1d", progress=False)
        if not hist.empty:
            c = hist['Close'].dropna().tolist()[:-1] # Remove today
            if len(c) > 30:
                m = calc_macd_state(c)
                e8 = get_ema_array(c, 8)
                e21 = get_ema_array(c, 21)
                if m in [1, 2] and e8[-1] is not None and e21[-1] is not None and e8[-1] < e21[-1]:
                    if (e8[-1] < e21[-1] and e8[-2] >= e21[-2]) or (e8[-2] < e21[-2] and e8[-3] >= e21[-3]):
                        dead_yesterday.append(t)
    except Exception as e:
        pass

print(f"Golden yesterday & today: {golden_yesterday}")
print(f"Dead yesterday & today: {dead_yesterday}")
