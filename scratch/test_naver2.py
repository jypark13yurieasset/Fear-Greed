import requests
from bs4 import BeautifulSoup

url = "https://finance.naver.com/item/main.naver?code=005930"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')

target_price_element = soup.find('th', text='목표주가')
if target_price_element:
    parent = target_price_element.find_parent('tr')
    print("Target Price block:", parent.text if parent else "Not found")

# Or search specifically for class
est = soup.select('.r_estimate')
print("Estimate block:", [e.text for e in est])

