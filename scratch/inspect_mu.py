import yfinance as yf
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta

ticker = "MU"
df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True)

# Extract close column as a clean Series with DatetimeIndex
if isinstance(df.columns, pd.MultiIndex):
    series = df['Close'][ticker].dropna()
else:
    series = df['Close'].dropna()

if series.index.tz is not None:
    series.index = series.index.tz_localize(None)

today_date = series.index[-1]
price = float(series.iloc[-1])

print(f"Today: {today_date.strftime('%Y-%m-%d')} | Price: {price:.2f}")

target_pcts = {
    "1W": 17.03,
    "1M": 54.92,
    "1Y": 817.47
}

for name, pct in target_pcts.items():
    target_price = price / (1 + pct / 100)
    print(f"\nTarget price for {name} ({pct:+.2f}%): {target_price:.2f}")
    
    # Calculate difference
    diff = (series - target_price).abs()
    closest_date = diff.idxmin()
    closest_price = float(series.loc[closest_date])
    closest_pct = (price - closest_price) / closest_price * 100
    days_ago = (today_date - closest_date).days
    print(f"  Closest Date: {closest_date.strftime('%Y-%m-%d')} | Price: {closest_price:.2f} | Chg: {closest_pct:+.2f}% | Days ago: {days_ago}")
    
    # Let's print dates around this target date to see what was nearby
    target_cal_date = today_date
    if name == "1W":
        target_cal_date = today_date - datetime.timedelta(days=7)
    elif name == "1M":
        target_cal_date = today_date - relativedelta(months=1)
    elif name == "1Y":
        target_cal_date = today_date - relativedelta(years=1)
        
    print(f"  Target Calendar Date: {target_cal_date.strftime('%Y-%m-%d')}")
    asof_date = series.index.asof(pd.Timestamp(target_cal_date))
    asof_price = float(series.loc[asof_date])
    asof_pct = (price - asof_price) / asof_price * 100
    print(f"  Asof Date: {asof_date.strftime('%Y-%m-%d')} | Price: {asof_price:.2f} | Chg: {asof_pct:+.2f}%")
