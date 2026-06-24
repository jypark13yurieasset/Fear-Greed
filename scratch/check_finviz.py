from curl_cffi import requests
from bs4 import BeautifulSoup
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_finviz_pe(ticker):
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    try:
        r = requests.get(url, headers=headers, impersonate="chrome110")
        if r.status_code != 200:
            print(f"{ticker} Status: {r.status_code}")
            return None, None
        soup = BeautifulSoup(r.text, 'html.parser')
        
        pe, fpe = None, None
        
        # the table has td elements, where text is 'P/E' and next sibling is the value
        tds = soup.find_all('td')
        for i, td in enumerate(tds):
            if td.text == 'P/E':
                pe_val = tds[i+1].text
                if pe_val != '-':
                    pe = float(pe_val)
            if td.text == 'Forward P/E':
                fpe_val = tds[i+1].text
                if fpe_val != '-':
                    fpe = float(fpe_val)
                    
        return pe, fpe
    except Exception as e:
        print(f"Error {ticker}: {e}")
        return None, None

print(get_finviz_pe('AAPL'))
print(get_finviz_pe('MSFT'))

