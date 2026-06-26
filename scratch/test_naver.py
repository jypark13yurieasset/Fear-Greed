import requests
from bs4 import BeautifulSoup

url = "https://finance.naver.com/item/main.naver?code=005930"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')

per = soup.select_one('#_per')
fwd_per = soup.select_one('#_cns_per')
target_price = soup.select_one('.r_estimate .num')

print("PER:", per.text if per else None)
print("Fwd PER:", fwd_per.text if fwd_per else None)
print("Target Price:", target_price.text if target_price else None)

