from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import re

def scrape_etf_com(ticker):
    url = f'https://www.etf.com/{ticker}'
    r = requests.get(url, impersonate='chrome')
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Try to find the holdings section and date
    date_str = None
    # Let's just print all text that matches "As of"
    for tag in soup.find_all(string=re.compile(r'As of')):
        print(f"Date match: {tag.strip()}")
        if re.search(r'\d{2}/\d{2}/\d{4}', tag):
            date_str = tag.strip()
    
    # Find table with Symbol, Holding, Allocation
    tables = soup.find_all('table')
    holdings = []
    for t in tables:
        headers = [th.get_text(strip=True) for th in t.find_all('th')]
        if 'Symbol' in headers and 'Allocation %' in headers:
            rows = t.find_all('tr')[1:] # skip header
            for row in rows[:10]: # Top 10
                cells = row.find_all('td')
                if len(cells) >= 3:
                    sym = cells[0].get_text(strip=True)
                    name = cells[1].get_text(strip=True)
                    alloc_str = cells[2].get_text(strip=True).replace('%', '')
                    try:
                        weight = float(alloc_str)
                        holdings.append({'ticker': sym, 'name': name, 'weight': weight})
                    except:
                        pass
    print(json.dumps({'date': date_str, 'holdings': holdings}, indent=2, ensure_ascii=False))

scrape_etf_com('ARKK')
