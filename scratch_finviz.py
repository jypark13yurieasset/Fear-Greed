import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://finviz.com/quote.ashx?t=AAPL', headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')
tds = soup.find_all('td')
for i, td in enumerate(tds):
    if td.text in ['Market Cap', 'Target Price']:
        print(td.text, tds[i+1].text)
