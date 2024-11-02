from flask import Flask, request, render_template, jsonify
import openai
import os  # For accessing environment variables
from dotenv import load_dotenv
import pandas as pd
import json

# Load environment variables from .env file
load_dotenv()

# Get the Azure API key and other necessary settings from the environment
azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment_name = os.getenv("DEPLOYMENT_NAME")

# Check if the API key is None and raise an error if not found
if azure_api_key is None:
    raise ValueError("AZURE_OPENAI_API_KEY not found in .env file.")

# Set the OpenAI API key and other configurations for Azure
openai.api_key = azure_api_key
openai.api_base = azure_endpoint  # Set the endpoint
openai.api_type = "azure"  # Specify the API type as Azure
openai.api_version = azure_api_version  # Set the API version
openai.deployment_name = deployment_name  # Set the deployment name

template_dir = os.path.abspath('../frontend/build')
static_dir = os.path.abspath('../frontend/static')

print(f"Template directory: {template_dir}")
print(f"Static directory: {static_dir}")

app = Flask(
    __name__, 
    static_folder=static_dir, 
    template_folder=template_dir)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/subreddit/<subreddit>')
def subreddit(subreddit):
    # You could fetch subreddit data here and return it as JSON
    return jsonify({'message': f'You selected subreddit {subreddit}'})

@app.route('/get_related_subreddits', methods=['POST'])
def get_related_subreddits():
    data = request.json
    topic = data.get('topic')
    print(topic)

    # Call your function to get relevant subreddits based on the topic
    related_subreddits = get_relevant_subreddits(topic)

    return jsonify({'related_subreddits': related_subreddits})

@app.route('/get_themes/<subreddit>', methods=['GET'])
def get_themes(subreddit):
    print(f"Requested subreddit: {subreddit}")  # Log the received subreddit
    # Create a prompt for the OpenAI API
    prompt = f"Generate a list of 6 themes that policymakers and policy researchers would be interested in learning more about, related to the subreddit '{subreddit}', each with a title ('title') and a very brief description ('description'). Return the themes in JSON format."

    # Call the OpenAI API to get themes
    try:
        response = openai.chat.completions.create(
            model=deployment_name,  # Specify your model
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        print(response)
        

        # Extract the content from the response
        themes_json = response.choices[0].message.content.strip()
        print("THEMES THEMES THEMES")
        print(themes_json)

        # Extract only the JSON part by removing the Markdown formatting
        # Assuming the JSON is wrapped in ```json ... ```
        json_start = themes_json.find("[")  # Find the start of the JSON array
        json_end = themes_json.rfind("]") + 1  # Find the end of the JSON array
        clean_json_string = themes_json[json_start:json_end]

        # Print the cleaned JSON string for debugging
        print("Cleaned JSON String:", clean_json_string)

        # Parse the cleaned JSON string to a Python dictionary
        themes_data = json.loads(clean_json_string)

        # Return the JSON response
        return jsonify(themes_data)

    except Exception as e:
        print(f"Error fetching themes: {e}")
        return jsonify({"error": "Failed to retrieve themes."}), 500
    
# Load the CSV file with subreddits
subreddits = pd.read_csv("data/subreddits.csv")['name'].tolist()

def get_relevant_subreddits(topic):
    # Process subreddits in chunks
    relevant_subreddits = []
    chunk_size = 200
    print(len(subreddits))

    for i in range(0, len(subreddits), chunk_size):
        subreddits_chunk = subreddits[i:i + chunk_size]
        prompt = f"Here is a list of subreddits: {subreddits_chunk}. Based on the topic '{topic}', please provide a list of the most relevant subreddits from the list. If there are multiple relevant subreddits, separate their names with commas. If none are relevant, respond with a blank line."
        # prompt = "how is the weather?"
        # Call the OpenAI API
        response = openai.chat.completions.create(
            model=deployment_name,
            messages=[{"role": "user", "content": prompt}]
        )

        print(response)
        
        # Retrieve and print response content if it exists
        if response.choices and response.choices[0].message.content:
            responses = response.choices[0].message.content.split(",")
            print(response.choices[0].message.content)
            for r in responses:
                relevant_subreddits.append(r)
        

    return relevant_subreddits


# def main():
#     relevant_subreddits = get_relevant_subreddits("Outdoor Seating")
#     for s in relevant_subreddits:
#         print(s)

# Run the main function
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050, debug=True)
