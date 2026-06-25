import pandas as pd
dates = pd.date_range("2024-01-01", "2024-05-01", freq="D")
series = pd.Series(range(len(dates)), index=dates)
print("Weekly:", series.resample("W").last().tolist())
try:
    print("Monthly M:", series.resample("M").last().tolist())
except Exception as e:
    print("Monthly ME:", series.resample("ME").last().tolist())
