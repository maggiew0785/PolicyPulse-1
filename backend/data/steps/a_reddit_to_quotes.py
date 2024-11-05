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

class EntriesOutput(BaseModel):
    entries: List[QuoteSummary]

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
            return response.json()
        elif response.status_code == 429:
            # Only retry rate limits
            retry_after = 60
            match = re.search(r'retry after (\d+) seconds', response.text)
            if match:
                retry_after = int(match.group(1))
            logging.warning(f"Rate limit hit: Waiting for {retry_after} seconds.")
            time.sleep(retry_after)
            raise Exception("Rate limit error")
        elif response.status_code == 400:
            # Check if it's a content filter response
            response_json = response.json()
            if 'error' in response_json and 'innererror' in response_json['error']:
                inner_error = response_json['error']['innererror']
                if inner_error.get('code') == 'ResponsibleAIPolicyViolation':
                    filter_result = inner_error.get('content_filter_result', {})
                    logging.info(f"Content filtered - Filter results: {filter_result}")
                    return None  # Don't retry, just return None for filtered content
        
        # For other errors, raise exception to retry
        raise Exception(f"Request failed: {response.status_code} - {response.text}")
    
    except Exception as e:
        if "Request failed: 400" in str(e) and "ResponsibleAIPolicyViolation" in str(e):
            logging.info("Content filtered by Azure OpenAI policy - skipping")
            return None
        logging.warning(f"API call failed: {str(e)}. Retrying...")
        raise


def process_file(file_path, output_dir):
    df = pd.read_csv(file_path)
    
    # Limit to first 300 rows
    df = df.head(5)
    
    # Debug print
    print(f"Total rows to process: {len(df)}")
    
    # Read existing processed IDs from the JSONL file
    processed_ids = set()
    output_subdir = os.path.join(output_dir, 'combined')  # Match your directory structure
    os.makedirs(output_subdir, exist_ok=True)
    output_path = os.path.join(output_subdir, 'combined_quotes.jsonl')
    
    if os.path.exists(output_path):
        print(f"Found existing file: {output_path}")
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if 'source_id' in data:
                        processed_ids.add(data['source_id'])
                except json.JSONDecodeError:
                    continue
    
    print(f"Found {len(processed_ids)} previously processed IDs")
    
    # Filter to only unprocessed rows
    unprocessed_rows = df[~df['id'].isin(processed_ids)]
    print(f"Found {len(unprocessed_rows)} new rows to process")

    if len(unprocessed_rows) == 0:
        print("No new rows to process!")
        return

    with Pool(POOL_SIZE) as pool:
        args = [(file_path, row, output_dir) for _, row in unprocessed_rows.iterrows()]
        for _ in tqdm(pool.imap_unordered(process_row, args), total=len(unprocessed_rows),
                      desc=f"Processing {os.path.basename(file_path)}"):
            time.sleep(2)

def process_row(args):
    file_path, row, output_dir = args
    subreddit = os.path.basename(file_path).split('_')[0]
    system_prompt = read_file(get_env('SYSTEM_PROMPT_PATH'))

    # Define output path
    output_subdir = os.path.join(output_dir, subreddit)
    os.makedirs(output_subdir, exist_ok=True)
    output_path = os.path.join(output_subdir, f'{subreddit}_quotes.jsonl')

    # Check if this row was already processed (double-check)
    processed_ids = set()
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    processed_ids.add(data.get('source_id'))
                except json.JSONDecodeError:
                    continue
    
    if row['id'] in processed_ids:
        return

    formatted_submission = {
        "Submission Title": row['title'],
        "Submission Body": row['selftext'],
        "Comments": row['body'],
        "ID": row['id']
    }

    user_prompt = json.dumps(formatted_submission, default=str)

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = make_api_call(messages)
        response_content = response['choices'][0].get('message', {}).get('content')
        if not response_content or response_content.strip() in ["null", "```json\nnull\n```"]:
            # logging.info(f"No relevant data for row {row['id']}")
            return

        # Clean the response content by removing markdown code block formatting
        cleaned_content = response_content
        if response_content.startswith("```json"):
            # Remove ```json from start and ``` from end
            cleaned_content = response_content.replace("```json", "", 1)
            cleaned_content = cleaned_content.replace("```", "", 1)
        
        # Strip any remaining whitespace
        cleaned_content = cleaned_content.strip()
        
        print(f"Cleaned content: {cleaned_content}")
        
        try:
            parsed_data = json.loads(cleaned_content)
            print(f"Successfully parsed JSON: {parsed_data}")
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            print(f"Content that failed to parse: {cleaned_content}")
            return

        if not parsed_data:
            print(f"No relevant data in parsed response for row {row['id']}")
            return

        parsed_output = EntriesOutput(
            entries=[QuoteSummary(**item) for item in parsed_data.get("entries", [])]
        )
        print(f"Parsed output: {parsed_output}")

        if parsed_output.entries:
            # Add row ID to each entry for traceability
            output_dict = parsed_output.dict()
            output_dict['source_id'] = row['id']
            print("inside right now")
            # Use a lock to prevent concurrent writes
            from filelock import FileLock
            lock_path = output_path + '.lock'
            
            with FileLock(lock_path):
                with open(output_path, 'a', encoding='utf-8') as file:
                    print("DUMPING SOMETHING??")
                    file.write(json.dumps(output_dict) + '\n')
                    file.flush()
                    os.fsync(file.fileno())  # Force write to disk
            
            logging.info(f"Successfully appended {len(parsed_output.entries)} entries for row {row['id']} to {output_path}")
        else:
            logging.info(f"No entries to save for row {row['id']}")

    except Exception as e:
        logging.error(f"Error processing row {row['id']} in {file_path}: {str(e)}")


# def process_file(file_path, output_dir):
#     df = pd.read_csv(file_path)
#     with Pool(POOL_SIZE) as pool:
#         args = [(file_path, row, output_dir) for _, row in df.iterrows()]
#         for _ in tqdm(pool.imap_unordered(process_row, args), total=len(df),
#                       desc=f"Processing {os.path.basename(file_path)}"):
#             time.sleep(2)  # Add a fixed delay (e.g., 1 second) between each request


def main(input_dir, output_dir):
    print(f"POOL_SIZE: {POOL_SIZE}, DEPLOYMENT_NAME: {DEPLOYMENT_NAME}, endpoint: {endpoint}, api_key: {api_key}")
    os.makedirs(output_dir, exist_ok=True)
    csv_files = [f for f in os.listdir(input_dir) if f.endswith('_llm.csv')]
    total_files = len(csv_files)
    print(f"Total Files: {total_files}")
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
