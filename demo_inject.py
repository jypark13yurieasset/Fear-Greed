import json
import os

DATA_DIR = "/Users/junyounggarypark/Documents/GitHub/Fear-Greed/data"
json_path = os.path.join(DATA_DIR, "index_constituents.json")
js_path = os.path.join(DATA_DIR, "index_constituents.js")

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for s in data['stocks']:
    if s['ticker'] == 'APP':
        s['golden_cross_count'] = 3
    elif s['ticker'] == 'SPGI':
        s['golden_cross_count'] = 2
    elif s['ticker'] == 'CSCO':
        s['dead_cross_count'] = 4
    elif s['ticker'] == 'GS':
        s['dead_cross_count'] = 2

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(f"const INDEX_DATA = {json.dumps(data, ensure_ascii=False, indent=2)};\n")

print("Demo counts injected into JSON/JS files.")
