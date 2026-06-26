import requests
from bs4 import BeautifulSoup
import re

url = "https://finance.naver.com/item/main.naver?code=005930"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')

# Find all em elements
ems = soup.find_all('em')
for em in ems:
    if '목표주가' in em.parent.text:
        print("Found:", em.parent.text)

for th in soup.find_all('th'):
    if '목표주가' in th.text:
        print("Found TH:", th.text)
        print("Parent:", th.parent.text)

# Also test finding the market cap
mcap = soup.select_one('#_market_sum')
print("Market Cap:", mcap.text.strip() if mcap else None)

