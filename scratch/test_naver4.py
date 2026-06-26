import requests
from bs4 import BeautifulSoup
import re

url = "https://finance.naver.com/item/main.naver?code=005930"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')

for th in soup.find_all('th'):
    if '목표주가' in th.text:
        td = th.find_next_sibling('td')
        if td:
            ems = td.find_all('em')
            if len(ems) >= 2:
                print("Target Price:", ems[1].text)
