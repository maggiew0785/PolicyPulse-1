import os
import json
import requests
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Sample row data for testing
row_data = {
    'id': 'test_id_001',
    'title': 'Test Submission Title',
    'selftext': 'Test submission body content.',
    'body': 'Test comment body content.'
}

class QuoteSummary(BaseModel):
    quote: str
    summary: str

class AIImpactAnalysis(BaseModel):
    anecdotes: List[QuoteSummary]
    media_reports: List[QuoteSummary]
    opinions: List[QuoteSummary]
    other: List[QuoteSummary]

def make_api_call(messages):
    # Load Azure OpenAI endpoint and API key from environment variables
    endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    api_key = os.getenv('AZURE_OPENAI_API_KEY')
    model = "gpt-4o"
    api_version = "2024-08-01-preview"

    # Set headers and request data for Azure OpenAI
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key  # Use 'api-key' for Azure OpenAI
    }
    data = {
        "messages": messages,
        "max_tokens": 100
    }

    # Make the request
    response = requests.post(
        f"{endpoint}/openai/deployments/{model}/chat/completions?api-version={api_version}",
        headers=headers, json=data
    )

    # Check if request was successful and return JSON response
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Request failed: {response.status_code} - {response.text}")

# Define a function to test
def test_process_row():
    try:
        messages = [
            {"role": "system", "content": "Summarize the following Reddit post."},
            {"role": "user", "content": json.dumps(row_data)}
        ]
        
        # Call the make_api_call function
        response = make_api_call(messages)
        
        # Parse response content as AIImpactAnalysis if structure is compatible
        parsed_output = AIImpactAnalysis(
            anecdotes=[
                QuoteSummary(quote=quote["content"], summary="Summarized content here")
                for quote in response.get("anecdotes", [])
            ],
            media_reports=[],
            opinions=[],
            other=[]
        )

        
        # Save parsed output to JSON file
        output_dir = "test_output"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'output-{row_data["id"]}.json')
        
        with open(output_path, 'w') as file:
            json.dump(parsed_output.dict(), file, indent=4)

        print(f"Successfully processed and saved output for row {row_data['id']} in {output_path}")
    except Exception as e:
        print(f"Error processing row {row_data['id']}: {str(e)}")

# Run test
test_process_row()
