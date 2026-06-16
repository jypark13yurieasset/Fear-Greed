
# Historical closing prices from Yahoo Finance
sp500 = {
    '2026-06-10': 7266.99,
    '2026-06-11': 7394.30,
    '2026-06-12': 7431.46,
    '2026-06-15': 7554.29,  # regularMarketPrice (Monday close)
}

nasdaq = {
    '2026-06-10': 25169.50,
    '2026-06-11': 25809.66,
    '2026-06-12': 25888.84,
    '2026-06-15': 26683.94,  # regularMarketPrice
}

vix = {
    '2026-06-10': 22.22,
    '2026-06-11': 19.44,
    '2026-06-12': 17.68,
    '2026-06-15': 16.20,  # regularMarketPrice
}

usd_krw = {
    '2026-06-10': 1525.05,
    '2026-06-11': 1517.38,
    '2026-06-12': 1509.50,  # FX: 6/14 is used as Fri close equivalent
    '2026-06-15': 1508.67,  # regularMarketPrice (latest)
}

def calc_change(current, previous):
    return round((current - previous) / previous * 100, 2)

# 2026-06-12 entry: shows 6/11 close, change = 6/11 vs 6/10
print("=== 2026-06-12 entry (price=6/11 close, change=6/11 vs 6/10) ===")
print(f"  S&P 500: price={sp500['2026-06-11']}, change={calc_change(sp500['2026-06-11'], sp500['2026-06-10'])}%")
print(f"  Nasdaq:  price={nasdaq['2026-06-11']}, change={calc_change(nasdaq['2026-06-11'], nasdaq['2026-06-10'])}%")
print(f"  VIX:     price={vix['2026-06-11']}, change={calc_change(vix['2026-06-11'], vix['2026-06-10'])}%")
print(f"  USD/KRW: price={usd_krw['2026-06-11']}, change={calc_change(usd_krw['2026-06-11'], usd_krw['2026-06-10'])}%")

# 2026-06-15 entry: shows 6/12 close, change = 6/12 vs 6/11
print("\n=== 2026-06-15 entry (price=6/12 close, change=6/12 vs 6/11) ===")
print(f"  S&P 500: price={sp500['2026-06-12']}, change={calc_change(sp500['2026-06-12'], sp500['2026-06-11'])}%")
print(f"  Nasdaq:  price={nasdaq['2026-06-12']}, change={calc_change(nasdaq['2026-06-12'], nasdaq['2026-06-11'])}%")
print(f"  VIX:     price={vix['2026-06-12']}, change={calc_change(vix['2026-06-12'], vix['2026-06-11'])}%")
print(f"  USD/KRW: price={usd_krw['2026-06-12']}, change={calc_change(usd_krw['2026-06-12'], usd_krw['2026-06-11'])}%")

# 2026-06-16 entry: shows 6/15 close, change = 6/15 vs 6/12
print("\n=== 2026-06-16 entry (price=6/15 close, change=6/15 vs 6/12) ===")
print(f"  S&P 500: price={sp500['2026-06-15']}, change={calc_change(sp500['2026-06-15'], sp500['2026-06-12'])}%")
print(f"  Nasdaq:  price={nasdaq['2026-06-15']}, change={calc_change(nasdaq['2026-06-15'], nasdaq['2026-06-12'])}%")
print(f"  VIX:     price={vix['2026-06-15']}, change={calc_change(vix['2026-06-15'], vix['2026-06-12'])}%")
print(f"  USD/KRW: price={usd_krw['2026-06-15']}, change={calc_change(usd_krw['2026-06-15'], usd_krw['2026-06-12'])}%")
