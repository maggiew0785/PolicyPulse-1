import os
import json
import openai
from dotenv import load_dotenv
from collections import Counter
from collections import defaultdict

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

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
deployment_name = get_env('DEPLOYMENT_NAME')
MAX_RETRIES = get_env('MAX_RETRIES', 5, int)
MIN_RETRY_WAIT = get_env('MIN_RETRY_WAIT', 1, int)
MAX_RETRY_WAIT = get_env('MAX_RETRY_WAIT', 60, int)

# Azure OpenAI settings
endpoint = get_env('AZURE_OPENAI_ENDPOINT')
api_key = get_env('AZURE_OPENAI_API_KEY')
api_version = get_env('AZURE_OPENAI_API_VERSION', '2024-08-01-preview')

# Set the OpenAI API key and other configurations for Azure
openai.api_key = api_key
openai.api_base = endpoint  # Set the endpoint
openai.api_type = "azure"  # Specify the API type as Azure
openai.api_version = api_version  # Set the API version
openai.deployment_name = deployment_name  # Set the deployment name
def read_json_files(directory):
    summaries = []
    all_quotes = []  # Store all quotes

    # Iterate through all JSON files in the specified directory
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r') as file:
                data = json.load(file)
                
                # Extract summaries and quotes from each relevant section
                for summary_list in [data.get('anecdotes', []), data.get('media_reports', []), data.get('opinions', []), data.get('other', [])]:
                    for entry in summary_list:
                        if 'summary' in entry:
                            summaries.append(entry['summary'])  # Assuming summary is the key
                        if 'quote' in entry:
                            all_quotes.append(entry['quote'])  # Assuming quote is the key

    return summaries, all_quotes

def get_themes_from_chatgpt(summaries):
    combined_summaries = "\n".join(summaries)
    prompt = (
        "Based on the following summaries, identify the top 5 common themes. "
        "Please return the results in the following format:\n"
        "{\n"
        '  "themes": [\n'
        '    "<theme1>",\n'
        '    "<theme2>",\n'
        '    "<theme3>",\n'
        '    "<theme4>",\n'
        '    "<theme5>"\n'
        '  ]\n'
        '}\n\n'
        f"{combined_summaries}"
    )

    response = openai.chat.completions.create(
        model=deployment_name,
        messages=[{"role": "user", "content": prompt}]
    )

    # Clean the response to extract just the JSON part
    raw_response = response.choices[0].message.content.strip()
    
    # Extract the JSON part from the response
    json_start_index = raw_response.find('{')  # Find the start of the JSON
    json_str = raw_response[json_start_index:]  # Get the JSON substring

    return json_str

def classify_quote_with_theme(quote, themes):
    prompt = (
        f"Please classify the following quote into one of these themes:\n"
        f"1. {themes[0]}\n"
        f"2. {themes[1]}\n"
        f"3. {themes[2]}\n"
        f"4. {themes[3]}\n"
        f"5. {themes[4]}\n\n"
        f"Quote: \"{quote}\"\n\n"
        f"Respond with the theme number (1-5) or 'none' if it doesn't fit any theme."
    )

    response = openai.chat.completions.create(
        model=deployment_name,  # Specify your model
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    print("HELLO????")
    print(response)

    return response.choices[0].message.content.strip()

def map_quotes_to_themes(all_quotes, themes):
    theme_quotes = defaultdict(list)

    for quote in all_quotes:
        theme_classification = classify_quote_with_theme(quote, themes)
        
        if theme_classification.isdigit() and 1 <= int(theme_classification) <= 5:
            theme_number = int(theme_classification) - 1  # Convert to 0-based index
            theme_quotes[themes[theme_number]].append(quote)

    print("HELLO!!!")

    print(theme_quotes)
    return theme_quotes

def main():
    directory = r'C:\Users\mwang\PolicyPulse\output_raw\combined'
    summaries, all_quotes = read_json_files(directory)
    
    if summaries:
        # Get the top 5 themes
        json_response = get_themes_from_chatgpt(summaries)
        try:
            # Parse the JSON response
            themes_data = json.loads(json_response)
            themes = themes_data['themes']

            # Map quotes to their respective themes
            theme_quotes = map_quotes_to_themes(all_quotes, themes)

            # Prepare final output
            output_data = {
                "themes": []
            }
            for theme in themes:
                output_data["themes"].append({
                    "theme": theme,
                    "quotes": theme_quotes[theme]
                })

            # Print the final output in JSON format
            print("Extracted themes and associated quotes:")
            print(json.dumps(output_data, indent=2))  # Pretty print the JSON response
        except json.JSONDecodeError as e:
            print("Error decoding JSON response:", e)
            print("Raw response:", json_response)
    else:
        print("No summaries found.")

if __name__ == '__main__':
    main()