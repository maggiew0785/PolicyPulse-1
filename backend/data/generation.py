import os
import json
import pandas as pd
import logging
import time
import random
import requests
from multiprocessing import Pool
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class QuoteSummary(BaseModel):
    quote: str
    summary: str

class AIImpactAnalysis(BaseModel):
    anecdotes: List[QuoteSummary]
    media_reports: List[QuoteSummary]
    opinions: List[QuoteSummary]
    other: List[QuoteSummary]

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to get environment variables with type conversion
def get_env(key, default=None, var_type=str):
    value = os.getenv(key, default)
    if value is None:
        return None
    if var_type == bool:
        return value.lower() in ('true', '1', 'yes', 'on')
    return var_type(value)

# Global variables
POOL_SIZE = get_env('POOL_SIZE', 2, int)
DEPLOYMENT_NAME = get_env('DEPLOYMENT_NAME')
MAX_RETRIES = get_env('MAX_RETRIES', 5, int)
MIN_RETRY_WAIT = get_env('MIN_RETRY_WAIT', 1, int)
MAX_RETRY_WAIT = get_env('MAX_RETRY_WAIT', 60, int)

# Azure OpenAI settings
endpoint = get_env('AZURE_OPENAI_ENDPOINT')
api_key = get_env('AZURE_OPENAI_API_KEY')
api_version = get_env('AZURE_OPENAI_API_VERSION', '2024-08-01-preview')

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()

import re
import time

@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=2, min=5, max=120),
    retry=retry_if_exception_type(Exception)
)
def make_api_call(messages):
    try:
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }
        data = {
            "messages": messages,
            "max_tokens": 4096
        }
        
        response = requests.post(
            f"{endpoint}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={api_version}",
            headers=headers, json=data
        )
        
        if response.status_code == 200:
            # logging.info("Raw API response: " + str(response.json()))  # Log the entire response
            return response.json()
        elif response.status_code == 429:
            # Extract retry-after seconds from the response message if present
            retry_after = 60  # Default to 60 seconds
            match = re.search(r'retry after (\d+) seconds', response.text)
            if match:
                retry_after = int(match.group(1))
            logging.warning(f"Rate limit hit: Waiting for {retry_after} seconds.")
            time.sleep(retry_after)
            raise Exception("Rate limit error")
        else:
            raise Exception(f"Request failed: {response.status_code} - {response.text}")
    
    except Exception as e:
        logging.warning(f"API call failed: {str(e)}. Retrying...")
        raise


def process_row(args):
    file_path, row, output_dir = args
    subreddit = os.path.basename(file_path).split('_')[0]
    system_prompt = read_file(get_env('SYSTEM_PROMPT_PATH'))

    formatted_submission = {
        "Submission Title": row['title'],
        "Submission Body": row['selftext'],
        "Comments": row['body'],
        "ID": row['id']
    }

    user_prompt = json.dumps(formatted_submission, default=str)

    # Define the output path based on row ID
    output_subdir = os.path.join(output_dir, subreddit)
    os.makedirs(output_subdir, exist_ok=True)
    output_path = os.path.join(output_subdir, f'output-{row["id"]}.json')

    # Check if the output file already exists
    if os.path.exists(output_path):
        logging.info(f"Output for row {row['id']} already exists. Skipping processing.")
        return  # Skip processing if the output already exists

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Make API call and parse the output
        response = make_api_call(messages)
        
        logging.info(f"response: {response}.")

        # Extract and parse the JSON content from the API response
        response_content = response['choices'][0]['message']['content']
        logging.info(f"response content: {response_content}.")

        parsed_data = json.loads(response_content)  # Parse the JSON string
        
        # Map parsed data to AIImpactAnalysis structure
        parsed_output = AIImpactAnalysis(
            anecdotes=[QuoteSummary(**item) for item in parsed_data.get("anecdotes", [])],
            media_reports=[QuoteSummary(**item) for item in parsed_data.get("media_reports", [])],
            opinions=[QuoteSummary(**item) for item in parsed_data.get("opinions", [])],
            other=[QuoteSummary(**item) for item in parsed_data.get("other", [])]
        )
        logging.info(f"parsed outputs: {parsed_output}.")

        # Only save the parsed output if it contains any non-empty field
        if parsed_output.anecdotes or parsed_output.media_reports or parsed_output.opinions or parsed_output.other:
            with open(output_path, 'w') as file:
                json.dump(parsed_output.dict(), file, indent=4)
            
            logging.info(f"Successfully processed and saved output for row {row['id']} in {output_path}")
        else:
            logging.info(f"Skipped saving empty output for row {row['id']}")

    except Exception as e:
        logging.error(f"Error processing row {row['id']} in {file_path}: {str(e)}")


def process_file(file_path, output_dir):
    df = pd.read_csv(file_path)
    with Pool(POOL_SIZE) as pool:
        args = [(file_path, row, output_dir) for _, row in df.iterrows()]
        for _ in tqdm(pool.imap_unordered(process_row, args), total=len(df),
                      desc=f"Processing {os.path.basename(file_path)}"):
            time.sleep(2)  # Add a fixed delay (e.g., 1 second) between each request


def main(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    csv_files = [f for f in os.listdir(input_dir) if f.endswith('_llm.csv')]
    total_files = len(csv_files)

    for i, csv_file in enumerate(csv_files, 1):
        file_path = os.path.join(input_dir, csv_file)
        logging.info(f"Processing file {i} of {total_files}: {csv_file}")
        process_file(file_path, output_dir)
        logging.info(f"Completed file {i} of {total_files}: {csv_file}")
        logging.info(f"Files remaining: {total_files - i}")

        time.sleep(random.uniform(1, 5))

if __name__ == '__main__':
    input_directory = get_env('INPUT_DIRECTORY')
    output_directory = get_env('OUTPUT_DIRECTORY')
    main(input_directory, output_directory)
