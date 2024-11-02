import requests
import json

api_key = 'f2a68a9d28cd4b2ab1c1f90a27eea4dc'  
endpoint = 'https://azure-openai-test-team10.openai.azure.com'

headers = {
    'Content-Type': 'application/json',
    'api-key': api_key
}

data = {
    "messages": [{"role": "user", "content": "Once upon a time"}],
    "max_tokens": 50
}

response = requests.post(f"{endpoint}/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview",
                         headers=headers, json=data)

if response.status_code == 200:
    result = response.json()
    print("Response:", result)
else:
    print("Error:", response.status_code, response.text)