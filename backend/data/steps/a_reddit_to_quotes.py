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
from filelock import FileLock
import string
from datetime import datetime
from string import Template
from typing import Dict
import hashlib

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class QuoteSummary(BaseModel):
    quote: str
    summary: str

class EntriesOutput(BaseModel):
    entries: List[QuoteSummary]

class PromptHandler:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.cache_dir = os.path.join(base_dir, "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def get_cache_key(self, subreddit: str, theme: str) -> str:
        """Generate a unique cache key for a subreddit-theme combination"""
        return hashlib.md5(f"{subreddit}:{theme}".encode()).hexdigest()
    
    def get_cached_output(self, subreddit: str, theme: str) -> str:
        """Check if we have cached results for this combination"""
        cache_key = self.get_cache_key(subreddit, theme)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.jsonl")
        if os.path.exists(cache_file):
            return cache_file
        return None

    def generate_prompt(self, template_path: str, params: Dict[str, str]) -> str:
        """Generate a prompt from template file with given parameters"""
        try:
            with open(template_path, 'r', encoding='utf-8') as file:
                template_content = file.read()
                template = string.Template(template_content)
                return template.safe_substitute(params)
        except Exception as e:
            print(f"Error reading template file: {e}")
            return None
    
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

def process_file(file_path, output_dir, subreddit, theme, prompt_params):
    df = pd.read_csv(file_path)
    df = df.head(150)
    
    # Sanitize subreddit and theme names for directory paths
    safe_subreddit = subreddit.replace('/', '_').replace(' ', '_')
    safe_theme = theme.replace(' ', '_')
    
    # Create specific output directory for this subreddit/theme combination
    output_subdir = os.path.join(output_dir, safe_subreddit, safe_theme)
    os.makedirs(output_subdir, exist_ok=True)
    output_path = os.path.join(output_subdir, 'combined_quotes.jsonl')
    
    print(f"Processing for specific combination: {subreddit} - {theme}")
    print(f"Output path: {output_path}")
    
    # Check for existing processed IDs only in this specific directory
    processed_ids = set()
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if 'source_id' in data:
                        processed_ids.add(data['source_id'])
                except json.JSONDecodeError:
                    continue

    unprocessed_rows = df[~df['id'].isin(processed_ids)]
    
    if len(unprocessed_rows) == 0:
        print("No new rows to process!")
        return

    with Pool(POOL_SIZE) as pool:
        args = [(file_path, row, output_subdir, subreddit, theme, prompt_params) 
                for _, row in unprocessed_rows.iterrows()]
        list(tqdm(pool.imap_unordered(process_row, args), 
                 total=len(unprocessed_rows),
                 desc=f"Processing {subreddit} - {theme}"))
    return output_subdir

def process_row(args):
    # Correctly unpack all arguments including prompt_params
    file_path, row, output_dir, subreddit, theme, prompt_params = args
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "..", "..", "prompts", "templates", "quote_extraction_template.txt")
    
    # Initialize PromptHandler with base_dir
    prompt_handler = PromptHandler(base_dir)
    
    # Use the prompt_params that were passed in, don't create new ones
    # print("Using Prompt Parameters:")
    # print(prompt_params)
    
    # Use the prompt handler to generate the prompt from the template file
    system_prompt = prompt_handler.generate_prompt(template_path, prompt_params)
    # if system_prompt:
    #     print("\nGenerated Prompt Content:")
    #     # print(system_prompt)
    # else:
    #     print(f"\nError: Could not generate prompt from template at {template_path}")
    
    # Create subreddit and theme specific output directory
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'combined_quotes.jsonl')
    # print("Output Path:")
    # print(output_path)
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
        # print("Got a response!")
        # print(response)
        if response is None:  # Handle case where API call returns None
            return
            
        response_content = response['choices'][0].get('message', {}).get('content')
        if not response_content or response_content.strip() in ["null", "```json\nnull\n```"]:
            return

        # Clean the response content by removing markdown code block formatting
        cleaned_content = response_content
        if response_content.startswith("```json"):
            cleaned_content = response_content.replace("```json", "", 1)
            cleaned_content = cleaned_content.replace("```", "", 1)
        
        cleaned_content = cleaned_content.strip()
        
        print(f"Cleaned content: {cleaned_content}")
        
        try:
            parsed_data = json.loads(cleaned_content)
            # print(f"Successfully parsed JSON: {parsed_data}")
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
        # print(f"Parsed output: {parsed_output}")

        if parsed_output.entries:
            # Add row ID and metadata to each entry
            output_dict = parsed_output.dict()
            output_dict.update({
                'source_id': row['id'],
                'subreddit': subreddit,
                'theme': theme,
                'processed_timestamp': datetime.now().isoformat()
            })
            
            # Use a lock to prevent concurrent writes
            lock_path = output_path + '.lock'
            
            with FileLock(lock_path):
                with open(output_path, 'a', encoding='utf-8') as file:
                    print("Writing to output file...")
                    file.write(json.dumps(output_dict) + '\n')
                    file.flush()
                    os.fsync(file.fileno())  # Force write to disk
            
            logging.info(f"Successfully appended {len(parsed_output.entries)} entries for row {row['id']} to {output_path}")
        else:
            logging.info(f"No entries to save for row {row['id']}")

    except Exception as e:
        logging.error(f"Error processing row {row['id']} in {file_path}: {str(e)}")


def main(input_dir, output_dir, subreddit, theme, prompt_params):
    """
    Main processing function
    Args:
        input_dir (str): Directory containing input files
        output_dir (str): Directory for output files
        subreddit (str): Selected subreddit (e.g., "r/ArtificialIntelligence")
        theme (str): Selected theme (e.g., "Data Privacy")
        prompt_params (dict): Parameters for template generation
    """
    print(f"Processing {subreddit} for theme: {theme}")
    print(f"POOL_SIZE: {POOL_SIZE}, DEPLOYMENT_NAME: {DEPLOYMENT_NAME}")
    
    os.makedirs(output_dir, exist_ok=True)
    csv_files = [f for f in os.listdir(input_dir) if f.endswith('_llm.csv')]
    total_files = len(csv_files)
    
    for i, csv_file in enumerate(csv_files, 1):
        file_path = os.path.join(input_dir, csv_file)
        logging.info(f"Processing file {i} of {total_files}: {csv_file}")
        # Pass prompt_params to process_file
        output_subdir = process_file(file_path, output_dir, subreddit, theme, prompt_params)
        logging.info(f"Completed file {i} of {total_files}: {csv_file}")

    return output_subdir