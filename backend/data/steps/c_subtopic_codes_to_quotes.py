'''
Input → Processing → Output
[quotes.jsonl]     [Azure OpenAI]     [categorized_quotes.jsonl]
[codes.json]   →   [categorization]   → [statistics]
'''
import os
import json
import requests
import logging
from dotenv import load_dotenv
from typing import List, Dict

# Load environment variables
load_dotenv()
base_dir = os.path.dirname(os.path.abspath(__file__))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_quote(quote: str) -> str:
   """Clean and escape quotes in the text."""
   # Replace any smart quotes with regular quotes
   quote = quote.replace('"', '"').replace('"', '"')
   # Escape any remaining double quotes
   quote = quote.replace('"', '\\"')
   return quote

def read_codes(analysis_file: str) -> Dict:
   """Read and format the codes from the analysis file."""
   with open(analysis_file, 'r', encoding='utf-8') as f:
       analysis = json.load(f)
   
   # Create a formatted dictionary of codes with numbers
   codes = {}
   for i, code in enumerate(analysis['codes'], 1):
       codes[i] = {
           'name': code['name'],
           'description': code['description']
       }
   return codes

def make_api_call(messages: List[Dict], model_config: Dict) -> Dict:
   """Make API call to Azure OpenAI."""
   headers = {
       "Content-Type": "application/json",
       "api-key": model_config['api_key']
   }
   
   data = {
       "messages": messages,
       "max_tokens": 4096,
       "temperature": 0.3
   }
   
   response = requests.post(
       f"{model_config['endpoint']}/openai/deployments/{model_config['deployment_name']}/chat/completions?api-version={model_config['api_version']}",
       headers=headers,
       json=data
   )
   
   if response.status_code == 200:
       return response.json()
   else:
       raise Exception(f"API call failed: {response.status_code} - {response.text}")

def categorize_quotes(quotes: List[Dict], codes: Dict, model_config: Dict) -> List[Dict]:
   """Categorize quotes using the API."""
   
   # Read the categorization prompt
   file_path = os.path.join(base_dir, "..", "..", "prompts", "c_categorize_quotes_prompt.txt")

   # Open the file and read its contents
   with open(file_path, 'r', encoding='utf-8') as f:
       system_prompt = f.read()
   
   # Format codes for the prompt
   codes_text = "Available codes:\n"
   for code_id, code_info in codes.items():
       codes_text += f"{code_id}. {code_info['name']}: {code_info['description']}\n"
   
   # Clean quotes before sending
   cleaned_quotes = []
   for quote in quotes:
       cleaned_quote = quote.copy()
       cleaned_quote['quote'] = clean_quote(quote['quote'])
       cleaned_quotes.append(cleaned_quote)
   
   # Prepare quotes text
   quotes_text = json.dumps(cleaned_quotes, indent=2)
   
   user_prompt = f"{codes_text}\n\nPlease categorize each of these quotes by assigning ALL relevant code numbers (1-10):\n{quotes_text}"
   
   messages = [
       {"role": "system", "content": system_prompt},
       {"role": "user", "content": user_prompt}
   ]

   response = make_api_call(messages, model_config)
   content = response['choices'][0]['message']['content']
   
   # Clean the response content
   if content.startswith("```json"):
       content = content.replace("```json", "", 1)
       content = content.replace("```", "", 1)
   content = content.strip()
   
   return json.loads(content)['categorized_quotes']

def main():
   # Configuration
   model_config = {
       'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
       'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
       'deployment_name': os.getenv('DEPLOYMENT_NAME'),
       'api_version': os.getenv('AZURE_OPENAI_API_VERSION', '2024-08-01-preview')
   }
   
   # Updated file paths
   analysis_file = os.path.join(base_dir, "..", "..", "..", "output", "output_quotes_ai", "combined", "summary_analysis.json")
#    analysis_file = os.path.join(base_dir, "..", "..", "output", "output_quotes_ai", "combined", "summary_analysis.json")
   input_file = os.path.join(base_dir, "..", "..", "..", "output", "output_quotes_ai", "combined", "combined_quotes.jsonl")
   output_file = os.path.join(base_dir, "..", "..", "..", "output", "output_quotes_ai", "combined", "categorized_quotes.jsonl")

   # Check if output file already exists
   if os.path.exists(output_file):
       print(f"Combined quote and codes file {output_file} already exists. Skipping matching.")
       return
   
   # Read codes
   print("Reading codes from analysis file...")
   codes = read_codes(analysis_file)
   
   print("\nCodes identified:")
   for code_id, code_info in codes.items():
       print(f"{code_id}. {code_info['name']}: {code_info['description']}")
   
   # Read quotes
   print("\nReading quotes from JSONL file...")
   quotes = []
   with open(input_file, 'r', encoding='utf-8') as f:
       for line in f:
           try:
               data = json.loads(line.strip())
               for entry in data.get('entries', []):
                   if 'quote' in entry:
                       quotes.append({
                           'quote': entry['quote'],
                           'source_id': data.get('source_id', 'unknown')
                       })
           except json.JSONDecodeError as e:
               print(f"Error parsing JSON line: {str(e)}")
               continue
   
   print(f"Found {len(quotes)} quotes")
   
   # Process in smaller batches
   batch_size = 5
   categorized_quotes = []
   
   print("\nCategorizing quotes in batches...")
   for i in range(0, len(quotes), batch_size):
       batch = quotes[i:i + batch_size]
       try:
           results = categorize_quotes(batch, codes, model_config)
           
           # Write results immediately
           with open(output_file, 'a', encoding='utf-8') as f:
               for quote in results:
                   f.write(json.dumps(quote) + '\n')
           
           categorized_quotes.extend(results)
           print(f"Processed batch {i//batch_size + 1} of {(len(quotes) + batch_size - 1)//batch_size}")
           
       except Exception as e:
           print(f"Error processing batch starting at index {i}: {str(e)}")
           continue
   
   # Generate statistics
   if categorized_quotes:
       code_counts = {}
       total_assignments = 0
       for quote in categorized_quotes:
           for code in quote.get('codes', []):
               code_name = code['code_name']
               code_counts[code_name] = code_counts.get(code_name, 0) + 1
               total_assignments += 1
       
       print("\nCode Distribution Statistics:")
       print("-" * 50)
       for code_name, count in sorted(code_counts.items(), key=lambda x: x[1], reverse=True):
           percentage = (count / len(quotes)) * 100
           print(f"{code_name}: {count} assignments ({percentage:.1f}% of quotes)")
       
       print(f"\nAverage codes per quote: {total_assignments / len(quotes):.1f}")
       print(f"\nResults saved to: {output_file}")
   else:
       print("No quotes were successfully categorized.")

if __name__ == "__main__":
   main()