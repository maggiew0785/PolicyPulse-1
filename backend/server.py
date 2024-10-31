from flask import Flask, request, render_template, jsonify
import openai
import os  # For accessing environment variables

openai.api_key = os.getenv("OPENAI_API_KEY")
import pandas as pd

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

    # Call your function to get relevant subreddits based on the topic
    related_subreddits = get_relevant_subreddits(topic)

    return jsonify({'related_subreddits': related_subreddits})

# Load the CSV file with subreddits
subreddits = pd.read_csv("data/subreddits.csv")['name'].tolist()

# Define the model type (ensure this is a valid model for your use case)
MODEL_TYPE = "gpt-4-0125-preview"
def get_relevant_subreddits(topic):
    # Process subreddits in chunks
    relevant_subreddits = []
    chunk_size = 100

    for i in range(0, len(subreddits), chunk_size):
        subreddits_chunk = subreddits[i:i + chunk_size]
        prompt = f"Here is a list of subreddits: {subreddits_chunk}. Which of these are most relevant to the topic '{topic}'? Your response should either be just the subreddits name separated by a comma, or blank if no subreddits are relevant."
        
        # Call the OpenAI API
        response = openai.chat.completions.create(
            model=MODEL_TYPE,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Retrieve and print response content if it exists
        if response.choices and response.choices[0].message.content:
            responses = response.choices[0].message.content.split(",")
            print(response.choices[0].message.content)
            for r in responses:
                relevant_subreddits.append(r)
        

    return relevant_subreddits

def main():
    relevant_subreddits = get_relevant_subreddits("Outdoor Seating")
    for s in relevant_subreddits:
        print(s)

# Run the main function
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050, debug=True)
