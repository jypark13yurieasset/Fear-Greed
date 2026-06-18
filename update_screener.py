#!/usr/bin/env python3
"""
Fetch constituents of S&P 500, Nasdaq-100, and Dow Jones Industrial Average
from Wikipedia using requests + pandas.
"""
import pandas as pd
import requests
import json
import os

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

results = {}

# --- 1. S&P 500 ---
print("=" * 60)
print("📊 S&P 500 구성종목 가져오는 중...")
try:
    resp = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", headers=headers)
    resp.raise_for_status()
    sp500_tables = pd.read_html(resp.text)
    sp500_df = sp500_tables[0]
    
    sp500_list = []
    for _, row in sp500_df.iterrows():
        sp500_list.append({
            'ticker': str(row.get('Symbol', row.iloc[0])).strip(),
            'name': str(row.get('Security', row.iloc[1])).strip(),
            'sector': str(row.get('GICS Sector', '')).strip(),
            'sub_industry': str(row.get('GICS Sub-Industry', '')).strip()
        })
    results['sp500'] = {
        'count': len(sp500_list),
        'constituents': sp500_list
    }
    print(f"   성공: {len(sp500_list)}개 종목 완료")
except Exception as e:
    print(f"   ❌ S&P 500 에러: {e}")

# --- 2. Nasdaq-100 ---
print("\n" + "=" * 60)
print("📊 Nasdaq-100 구성종목 가져오는 중...")
try:
    resp = requests.get("https://en.wikipedia.org/wiki/Nasdaq-100", headers=headers)
    resp.raise_for_status()
    ndx_tables = pd.read_html(resp.text)
    
    ndx_df = None
    for idx, t in enumerate(ndx_tables):
        cols_str = ' '.join([str(c).lower() for c in t.columns])
        if ('ticker' in cols_str or 'company' in cols_str) and len(t) >= 90:
            ndx_df = t
            print(f"   테이블 #{idx} 선택 (행: {len(t)})")
            break
            
    if ndx_df is None:
        for idx, t in enumerate(ndx_tables):
            if len(t) >= 50:
                ndx_df = t
                print(f"   테이블 #{idx} 선택(fallback) (행: {len(t)})")
                break
                
    if ndx_df is not None:
        ticker_col = company_col = None
        for c in ndx_df.columns:
            cl = str(c).lower()
            if 'ticker' in cl or 'symbol' in cl:
                ticker_col = c
            if 'company' in cl or 'security' in cl or 'name' in cl:
                company_col = c
        ticker_col = ticker_col or ndx_df.columns[1]
        company_col = company_col or ndx_df.columns[0]
        
        ndx_list = []
        for _, row in ndx_df.iterrows():
            ndx_list.append({
                'ticker': str(row[ticker_col]).strip(),
                'name': str(row[company_col]).strip()
            })
        results['nasdaq100'] = {
            'count': len(ndx_list),
            'constituents': ndx_list
        }
        print(f"   성공: {len(ndx_list)}개 종목 완료")
    else:
        print("   ❌ Nasdaq-100 테이블을 찾지 못했습니다.")
except Exception as e:
    print(f"   ❌ Nasdaq-100 에러: {e}")

# --- 3. Dow Jones ---
print("\n" + "=" * 60)
print("📊 Dow Jones Industrial Average 구성종목 가져오는 중...")
try:
    resp = requests.get("https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average", headers=headers)
    resp.raise_for_status()
    dow_tables = pd.read_html(resp.text)
    
    dow_df = None
    for idx, t in enumerate(dow_tables):
        cols_str = ' '.join([str(c).lower() for c in t.columns])
        if ('symbol' in cols_str or 'ticker' in cols_str) and (len(t) == 30 or len(t) == 31):
            dow_df = t
            print(f"   테이블 #{idx} 선택 (행: {len(t)})")
            break
            
    if dow_df is not None:
        ticker_col = company_col = sector_col = None
        for c in dow_df.columns:
            cl = str(c).lower()
            if 'symbol' in cl or 'ticker' in cl:
                ticker_col = c
            if 'company' in cl or 'name' in cl:
                company_col = c
            if 'sector' in cl:
                sector_col = c
        ticker_col = ticker_col or 'Symbol'
        company_col = company_col or 'Company'
        sector_col = sector_col or 'Sector'
        
        dow_list = []
        for _, row in dow_df.iterrows():
            dow_list.append({
                'ticker': str(row[ticker_col]).strip(),
                'name': str(row[company_col]).strip(),
                'sector': str(row[sector_col]).strip() if sector_col in dow_df.columns else ''
            })
        results['dowjones'] = {
            'count': len(dow_list),
            'constituents': dow_list
        }
        print(f"   성공: {len(dow_list)}개 종목 완료")
    else:
        print("   ❌ Dow Jones 테이블을 찾지 못했습니다.")
except Exception as e:
    print(f"   ❌ Dow Jones 에러: {e}")

# --- Summary ---
print("\n" + "=" * 60)
print("📋 요약")
print("=" * 60)
for idx_name, data in results.items():
    print(f"  {idx_name.upper():12s}: {data['count']}개 종목")

# Save JSON
import datetime
kst_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
results['date'] = kst_date.strftime("%Y-%m-%d")

output_dir = "/Users/junyounggarypark/Documents/GitHub/Fear-Greed/data"
os.makedirs(output_dir, exist_ok=True)
json_path = os.path.join(output_dir, "index_constituents.json")
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n✅ JSON 데이터가 {json_path}에 저장되었습니다.")

# Save JS (Global Variable)
js_path = os.path.join(output_dir, "index_constituents.js")
with open(js_path, 'w', encoding='utf-8') as f:
    f.write(f"const INDEX_DATA = {json.dumps(results, ensure_ascii=False, indent=2)};\n")
print(f"✅ JS 데이터가 {js_path}에 저장되었습니다.")
