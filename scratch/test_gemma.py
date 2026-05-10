import requests, base64

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
stream = False

headers = {
  "Authorization": "Bearer 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",
  "Accept": "application/json"
}

payload = {
  "model": "google/gemma-4-31b-it",
  "messages": [
    {
      "role": "user",
      "content": "What is in this image?"
    }
  ],
  "max_tokens": 1024,
  "temperature": 1.00,
  "top_p": 0.95,
  "stream": stream,
}

response = requests.post(invoke_url, headers=headers, json=payload)
print(response.json())
