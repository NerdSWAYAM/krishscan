import requests, base64

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"

headers = {
  "Authorization": "Bearer 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",
  "Accept": "application/json"
}

# 1x1 pixel JPEG
valid_jpg_b64 = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
# Actually that was the one that failed. Let's make a real 1x1 pixel image
with open("scratch/valid_b64.txt", "r") as f:
    b64_data = f.read().strip()

payload = {
  "model": "google/gemma-4-31b-it",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "What is in this image?"},
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
print(response.status_code)
print(response.json())
