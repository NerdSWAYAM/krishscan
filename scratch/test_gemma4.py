import requests, base64

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"

headers = {
  "Authorization": "Bearer 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",
  "Accept": "application/json"
}

with open("scratch/valid_b64.txt", "r") as f:
    b64_data = f.read().strip()

payload = {
  "model": "google/gemma-4-31b-it",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "Analyze this crop image and identify the disease. You MUST return ONLY a valid JSON object. The JSON should have exactly two keys: 'disease' (string, the name of the disease or 'Healthy Crop' or 'Unknown') and 'confidence' (number between 0 and 100, representing your confidence score). Do not include markdown formatting or any other text."},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_data}"}}
      ]
    }
  ],
  "max_tokens": 1024,
  "temperature": 0.2,
  "top_p": 0.95,
  "stream": False,
}

response = requests.post(invoke_url, headers=headers, json=payload)
print(response.json())
