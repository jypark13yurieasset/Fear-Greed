import os
import json
import datetime
import requests
from bs4 import BeautifulSoup

# 1. CNN Fear and Greed 최신 공식 데이터 API 주소 (2026년 최신 반영)
url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

fng_value = None

try:
    # API 요청 시도
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        # 최근 마감 점수(score)를 정수로 변환
        fng_value = int(round(data['fear_and_greed']['score']))
        print(f"API 호출 성공! 추출한 지수: {fng_value}")
    else:
        print(f"API 실패 (상태코드: {response.status_code}), 웹 스크래핑 백업 모드로 전환합니다.")

except Exception as api_err:
    print(f"API 접근 중 에러 발생: {api_err}, 웹 스크래핑 백업 모드로 전환합니다.")


# [백업 모드] API가 막히거나 주소가 또 바뀌었을 때 웹페이지 파싱 시도
if fng_value is None:
    try:
        web_url = "https://edition.cnn.com/markets/fear-and-greed"
        web_response = requests.get(web_url, headers=headers, timeout=10)
        soup = BeautifulSoup(web_response.text, 'html.parser')
        
        # 구조 내 텍스트 중 ratingValue 값을 역추적
        import re
        match = re.search(r'"ratingValue"\s*:\s*(\d+)', web_response.text)
        if match:
            fng_value = int(match.group(1))
            print(f"백업 웹 스크래핑 성공! 추출한 지수: {fng_value}")
        else:
            # 텍스트에서 직접 찾기 시도
            container = soup.find(text=re.compile(r"Fear & Greed Index is at"))
            if container:
                fng_value = int(re.search(r'\d+', container).group())
            else:
                raise Exception("모든 추출 경로에서 데이터를 찾지 못했습니다.")
    except Exception as web_err:
        print(f"백업 스크래핑도 실패했습니다: {web_err}")
        fng_value = 50 # 완전 실패 시 기본값 세팅


# 2. 기존 JSON 데이터 읽기 및 업데이트
today_str = datetime.date.today().isoformat()
json_file = "data.json"

if os.path.exists(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        try:
            dashboard_data = json.load(f)
        except json.JSONDecodeError:
            dashboard_data = {}
else:
    dashboard_data = {}

# 오늘 날짜 기준으로 데이터 기록
dashboard_data[today_str] = {
    "fear_and_greed": fng_value
}

# 3. JSON 파일로 다시 저장
with open(json_file, "w", encoding="utf-8") as f:
    json.dump(dashboard_data, f, indent=4, ensure_ascii=False)

print(f"--- 작업 완료 ---")
print(f"최종 저장 결과 -> 날짜: {today_str}, 지수: {fng_value}")
