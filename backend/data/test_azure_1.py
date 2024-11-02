import os
import requests
from dotenv import load_dotenv

load_dotenv("C:\\Users\\mwang\\PolicyPulse\\PolicyPulse\\backend\\data\\.env")

# Set up variables
endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
api_key = os.getenv('AZURE_OPENAI_API_KEY')
model = "gpt-4o"  # Update as needed
api_version = "2024-08-01-preview"  # Example version; update as needed

# Define headers and payload
headers = {
    "api-key": api_key,  # Use 'api-key' for Azure instead of 'Authorization'
    "Content-Type": "application/json"
}
data = {
    "messages": [
        {"role": "system", "content": "Summarize the following discussion on Uber."},
        {"role": "user", "content": "This is the sample content to summarize."}
    ],
    "max_tokens": 100
}

# Make the request
response = requests.post(f"{endpoint}/openai/deployments/{model}/chat/completions?api-version={api_version}",
                         headers=headers, json=data)

# Check response and handle errors
if response.status_code == 200:
    print(response.json())
else:
    print(f"Error: {response.status_code} - {response.text}")
