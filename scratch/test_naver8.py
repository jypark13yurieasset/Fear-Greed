import requests
from bs4 import BeautifulSoup
import re

url = "https://finance.naver.com/item/main.naver?code=005930"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')

fwd_per = soup.select_one('#_cns_per')
if fwd_per:
    table = fwd_per.find_parent('table')
    if table:
        print(table.text.strip())
