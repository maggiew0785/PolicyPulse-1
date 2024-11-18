import json
import os
from typing import List
import requests
from dotenv import load_dotenv

# Load environment variables
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, "..", "data", ".env"))

def read_jsonl_summaries(file_path: str) -> List[str]:
    """Read JSONL file and extract all summaries."""
    summaries = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            try:
                # Parse each line as JSON
                data = json.loads(line.strip())
                # Extract summaries from entries
                for entry in data.get('entries', []):
                    if 'summary' in entry:
                        summaries.append(entry['summary'])
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON line: {e}")
                continue
    return summaries

def analyze_summaries(summaries: List[str]) -> dict:
    """Send summaries to Azure OpenAI for analysis."""
    
    # Read the system prompt from file
    file_path = os.path.join(base_dir, "..", "..", "prompts", "b_analyze_summaries_prompt.txt")

    # Open the file and read its contents
    with open(file_path, 'r', encoding='utf-8') as f:
        system_prompt = f.read()
    
    user_prompt = f"Here are {len(summaries)} summaries to analyze:\n\n" + "\n".join(summaries)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # Make API call
    endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    api_key = os.getenv('AZURE_OPENAI_API_KEY')
    deployment_name = os.getenv('DEPLOYMENT_NAME')
    api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-08-01-preview')

    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    data = {
        "messages": messages,
        "max_tokens": 4096
    }
    
    response = requests.post(
        f"{endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}",
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        content = response.json()['choices'][0]['message']['content']
        # Clean the response content if it contains markdown formatting
        if content.startswith("```json"):
            content = content.replace("```json", "", 1)
            content = content.replace("```", "", 1)
        content = content.strip()
        return json.loads(content)
    else:
        raise Exception(f"API call failed: {response.status_code} - {response.text}")

def main():
    # Path to your JSONL file

    # Define the full path to `output_quotes_ai/combined`
    file_path = os.path.join(base_dir, "..", "..", "..","output", "output_quotes_ai", "combined")
    # file_path = os.path.join(base_dir, "..", "..", "output", "output_quotes_ai", "combined")

    # Define the output path for the JSON file
    output_path = os.path.join(file_path, 'summary_analysis.json')
    
    # Check if output file already exists
    if os.path.exists(output_path):   
        print(f"Analysis file {output_path} already exists. Skipping analysis.")
        return
      
    # Get all JSONL files in the directory
    jsonl_files = []
    for root, dirs, files in os.walk(file_path):
        for file in files:
            if file.endswith('_quotes.jsonl'):
                jsonl_files.append(os.path.join(root, file))
    
    all_summaries = []
    
    # Read summaries from all JSONL files
    for file_path in jsonl_files:
        print(f"Processing file: {file_path}")
        file_summaries = read_jsonl_summaries(file_path)
        all_summaries.extend(file_summaries)
    
    print(f"Total summaries found: {len(all_summaries)}")
    
    # Analyze the summaries
    try:
        results = analyze_summaries(all_summaries)
        
        # Print results in a formatted way
        print("\nTop 9 Codes Analysis:")
        print("-" * 50)
        for code in results['codes']:
            print(f"\nCode: {code['name']}")
            print(f"Percentage: {code['percentage']}")
            print(f"Description: {code['description']}")
        
        # Save results to a file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_path}")
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")

if __name__ == "__main__":
    main()