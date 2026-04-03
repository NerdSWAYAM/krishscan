import requests
import pandas as pd
import dotenv
import os

# Load environment variables
dotenv.load_dotenv()

API_KEY = os.getenv("API_KEY")
RESOURCE_ID = os.getenv("RESOURCE_ID")

url = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

params = {
    "api-key": API_KEY,
    "format": "json",   # ✅ MUST be json
    "limit": 1000
}

all_records = []

# Fetch data with pagination
for offset in range(0, 5000, 1000):
    params["offset"] = offset
    res = requests.get(url, params=params)

    if res.status_code != 200:
        print("❌ Error:", res.status_code)
        break

    data = res.json()

    if "records" not in data or not data["records"]:
        break

    all_records.extend(data["records"])

# Convert to DataFrame
df = pd.DataFrame(all_records)

# Check if data exists
if df.empty:
    print("⚠️ No data fetched")
    exit()

# Extract unique values
states = df['state'].dropna().unique()
districts = df['district'].dropna().unique()
markets = df['market'].dropna().unique()
commodities = df['commodity'].dropna().unique()

print("States:", states)
print("Districts:", districts[:20])
print("Markets:", markets[:20])
print("Commodities:", commodities[:20])

# Select useful columns
selected_columns = ['state', 'district', 'market', 'commodity', 'modal_price']

# Save CSV
output_file = "mandi_prices.csv"
df[selected_columns].to_csv(output_file, index=False)

print(f"✅ Data saved successfully to {output_file}")