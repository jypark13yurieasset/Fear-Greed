import requests
from bs4 import BeautifulSoup

url = "https://finance.naver.com/item/main.naver?code=005930"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')

mcap = soup.select_one('#_market_sum')
print("Market Cap:", mcap.text.strip().replace('\t', '').replace('\n', '') if mcap else "None")
