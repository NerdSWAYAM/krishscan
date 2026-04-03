import dotenv
import requests
import os
dotenv.load_dotenv()

API_KEY = os.getenv("API_KEY")
RESOURCE_ID = os.getenv("RESOURCE_ID")

url = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

params = {
    "api-key": API_KEY,
    "format": "json",
    "filters[state]": "Karnataka",
    "filters[commodity]": "Rice",
    "limit": 20  # number of records
}

response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print("Error:", response.status_code)