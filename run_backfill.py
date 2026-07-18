import json
import yfinance as yf

DATA_PATH = "data.json"

def get_price_and_change(ticker, date_str, prev_price):
    try:
        hist = yf.download(ticker, start=date_str, end="2026-07-14", progress=False)
        if not hist.empty and date_str in hist.index.strftime('%Y-%m-%d'):
            price = hist.loc[date_str]['Close'].item()
            change = round((price - prev_price) / prev_price * 100, 2)
            return round(price, 2), change
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
    return None, None

def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    if "2026-07-13" in data:
        print("2026-07-13 data already exists.")
        return
        
    if "2026-07-10" not in data:
        print("Missing 2026-07-10 base data.")
        return
        
    prev_data = data["2026-07-10"]
    new_data = prev_data.copy()
    
    # Update SPX
    spx_price, spx_change = get_price_and_change("^GSPC", "2026-07-13", prev_data["sp500_price"])
    if spx_price:
        new_data["sp500_price"] = spx_price
        new_data["sp500_change"] = spx_change
        
    # Update NDX
    ndx_price, ndx_change = get_price_and_change("^IXIC", "2026-07-13", prev_data["nasdaq_price"])
    if ndx_price:
        new_data["nasdaq_price"] = ndx_price
        new_data["nasdaq_change"] = ndx_change
        
    # Update VIX
    vix_price, vix_change = get_price_and_change("^VIX", "2026-07-13", prev_data["vix_price"])
    if vix_price:
        new_data["vix_price"] = vix_price
        new_data["vix_change"] = vix_change
        
    # Update DXY
    dxy_price, dxy_change = get_price_and_change("DX-Y.NYB", "2026-07-13", prev_data["dxy_price"])
    if dxy_price:
        new_data["dxy_price"] = dxy_price
        new_data["dxy_change"] = dxy_change
        
    data["2026-07-13"] = new_data
    
    # Optional: Fill 2026-06-29 if missing
    if "2026-06-29" not in data and "2026-06-26" in data:
        prev_26 = data["2026-06-26"]
        new_29 = prev_26.copy()
        
        spx_p, spx_c = get_price_and_change("^GSPC", "2026-06-29", prev_26["sp500_price"])
        if spx_p: new_29["sp500_price"] = spx_p; new_29["sp500_change"] = spx_c
        
        ndx_p, ndx_c = get_price_and_change("^IXIC", "2026-06-29", prev_26["nasdaq_price"])
        if ndx_p: new_29["nasdaq_price"] = ndx_p; new_29["nasdaq_change"] = ndx_c
        
        vix_p, vix_c = get_price_and_change("^VIX", "2026-06-29", prev_26["vix_price"])
        if vix_p: new_29["vix_price"] = vix_p; new_29["vix_change"] = vix_c
        
        dxy_p, dxy_c = get_price_and_change("DX-Y.NYB", "2026-06-29", prev_26["dxy_price"])
        if dxy_p: new_29["dxy_price"] = dxy_p; new_29["dxy_change"] = dxy_c
            
        data["2026-06-29"] = new_29
        print("Backfilled 2026-06-29.")
        
    # Sort dict by date keys
    sorted_data = {k: data[k] for k in sorted(data.keys())}
    
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=2)
        
    print("Backfilled 2026-07-13 and sorted data.json successfully.")
    
    # Also need to update data.js
    with open("data.js", "w", encoding="utf-8") as f:
        f.write("const DASHBOARD_DATA = ")
        json.dump(sorted_data, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print("Updated data.js")

if __name__ == "__main__":
    main()
