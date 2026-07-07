import requests
from bs4 import BeautifulSoup

url = 'https://www.slickcharts.com/nasdaq100'
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')
table = soup.find('table', {'class': 'table table-hover table-borderless table-sm'})
found = False
for row in table.find('tbody').find_all('tr'):
    cols = row.find_all('td')
    if len(cols) > 2:
        ticker = cols[2].text.strip()
        if ticker == 'SPCX':
            found = True
            print("YES, SPCX is in SlickCharts Nasdaq 100!")
if not found:
    print("NO, SPCX is not in SlickCharts Nasdaq 100.")
