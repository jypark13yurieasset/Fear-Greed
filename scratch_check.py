import json
import os

DATA_DIR = "/Users/junyounggarypark/Documents/GitHub/Fear-Greed/data"
signals_path = os.path.join(DATA_DIR, "index_constituents.json")

with open(signals_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Checking JSON for golden/dead...")
golden = [s['ticker'] for s in data['stocks'] if s.get('is_golden_cross_opportunity')]
dead = [s['ticker'] for s in data['stocks'] if s.get('is_danger_dead_cross')]

print(f"Golden today: {golden}")
print(f"Dead today: {dead}")
