import yfinance as yf
import time
from concurrent.futures import ThreadPoolExecutor

tickers = ["AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "UNH", "JNJ"]
def fetch_info(t):
    try:
        info = yf.Ticker(t).info
        return t, info.get("trailingPE"), info.get("forwardPE")
    except Exception:
        return t, None, None

start = time.time()
with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(fetch_info, tickers))
end = time.time()

print(f"Time taken for 10 tickers: {end-start:.2f} seconds")
print(results)
