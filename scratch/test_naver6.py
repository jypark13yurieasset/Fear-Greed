import requests
from bs4 import BeautifulSoup
import re

url = "https://finance.naver.com/item/main.naver?code=005930"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')

# find "목표주가" in text
elements = soup.find_all(text=re.compile('목표주가'))
for e in elements:
    parent = e.parent
    for _ in range(3):
        if parent:
            parent = parent.parent
    if parent:
        print("--- BLOCK ---")
        print(parent.text.strip())

