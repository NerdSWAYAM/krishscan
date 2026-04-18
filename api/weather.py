import requests

url = "https://api.openweathermap.org/data/2.5/weather"

params = {
    "q": "Bangalore",
    "appid": "8b8b14cc886cfa025bf91a1b6eb972e0",
    "units": "metric"
}

res = requests.get(url, params=params)
data = res.json()

print(data)