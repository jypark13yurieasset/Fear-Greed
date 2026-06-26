import requests
from bs4 import BeautifulSoup
import re

url = "https://finance.naver.com/item/main.naver?code=005930"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')

per = soup.select_one('#_per')
print("PER:", per.text if per else "None")

fwd_per = soup.select_one('#_cns_per')
print("Fwd PER:", fwd_per.text if fwd_per else "None")

target = soup.select_one('.r_estimate em')
if target:
    print("Target Price via .r_estimate em:", target.text)
else:
    print("Target Price via .r_estimate em: None")

mcap = soup.select_one('#_market_sum')
print("Market Cap:", mcap.text.strip().replace('\t', '').replace('\n', '') if mcap else "None")

