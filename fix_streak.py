import json
import os

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
log_path = os.path.join(data_dir, "signal_log.json")
sig_path = os.path.join(data_dir, "screener_signals.json")

# 1. Clean up July 9th logs from signal_log.json
with open(log_path, 'r') as f:
    logs = json.load(f)

cleaned_logs = [log for log in logs if log['date'] != '2026-07-09']

with open(log_path, 'w') as f:
    json.dump(cleaned_logs, f, indent=2, ensure_ascii=False)

# 2. Reconstruct screener_signals.json based on highest streak up to July 8
with open(sig_path, 'r') as f:
    sigs = json.load(f)

# Reset all to 0 first
for t in sigs:
    sigs[t] = {'type': None, 'count': 0, 'last_seen': ''}

# Find latest streak for each ticker up to July 8
latest_streaks = {}
for log in cleaned_logs:
    t = log['ticker']
    if t not in latest_streaks or log['date'] > latest_streaks[t]['date']:
        latest_streaks[t] = log

# Apply to sigs
for t, log in latest_streaks.items():
    sigs[t]['type'] = log['type']
    sigs[t]['count'] = log['streak']
    sigs[t]['last_seen'] = log['date']

with open(sig_path, 'w') as f:
    json.dump(sigs, f, indent=2)

print("Restored state to end of 2026-07-08. Ready to re-run for July 9.")
