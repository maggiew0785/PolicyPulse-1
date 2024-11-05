from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv
import pandas as pd
import json
from threading import Thread
import logging
from data.steps.a_reddit_to_quotes import main as reddit_quotes_main
from data.steps.b_json_to_subtopics import main as subtopics_main
from data.steps.c_subtopic_codes_to_quotes import main as codes_quotes_main

# Load environment variables
load_dotenv()

template_dir = os.path.abspath('../frontend/build')  # Points to where index.html is
static_dir = os.path.abspath('../frontend/static')   # Points to where main.js and main.css are

app = Flask(__name__, 
    static_folder=static_dir, 
    template_folder=template_dir)
CORS(app)  # Add this line to enable CORS

# Azure OpenAI Configuration
azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment_name = os.getenv("DEPLOYMENT_NAME")

if azure_api_key is None:
    raise ValueError("AZURE_OPENAI_API_KEY not found in .env file.")

# Configure OpenAI
openai.api_key = azure_api_key
openai.api_base = azure_endpoint
openai.api_type = "azure"
openai.api_version = azure_api_version
openai.deployment_name = deployment_name

# Flask app configuration
template_dir = os.path.abspath('../frontend/build')
static_dir = os.path.abspath('../frontend/static')

app = Flask(__name__, 
    static_folder=static_dir, 
    template_folder=template_dir)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Processing status tracker
processing_status = {
    'is_processing': False,
    'current_stage': None,
    'error': None,
    'progress': 0
}

@app.route('/')
def index():
    return render_template('index.html')

def run_processing_pipeline():
    """Run all processing scripts in sequence"""
    try:
        # Start reddit quotes collection
        processing_status.update({
            'is_processing': True,
            'current_stage': 'reddit_quotes',
            'error': None,
            'progress': 0
        })
        
        # Define input and output directories
        input_directory = r"C:\Users\mwang\PolicyPulse\output_raw_ai" 
        output_directory = r"C:\Users\mwang\PolicyPulse\output_quotes_ai"
        
        logger.info("Starting Reddit data collection...")
        reddit_quotes_main(input_directory, output_directory)
        processing_status['progress'] = 33
        
        # Start subtopics generation
        processing_status['current_stage'] = 'subtopics'
        logger.info("Starting subtopics analysis...")
        subtopics_main()
        processing_status['progress'] = 66
        
        # Start code-quote mapping
        processing_status['current_stage'] = 'code_mapping'
        logger.info("Starting code-quote mapping...")
        codes_quotes_main()
        processing_status['progress'] = 100
        
        logger.info("Processing completed successfully")
        
    except Exception as e:
        processing_status['error'] = str(e)
        logger.error(f"Error during processing: {e}")
        
    finally:
        processing_status.update({
            'is_processing': False,
            'current_stage': None
        })

@app.route('/api/theme-quotes', methods=['POST'])
def get_theme_quotes():
    """Get quotes for selected themes"""
    try:
        data = request.json
        selected_themes = data.get('themes', [])
        
        if not selected_themes:
            return jsonify({
                'status': 'error',
                'message': 'No themes selected'
            }), 400
            
        # Path to your files
        categorized_quotes_path = r"C:\Users\mwang\PolicyPulse\output_quotes_ai\combined\categorized_quotes.jsonl"
        codes_file_path = r"C:\Users\mwang\PolicyPulse\output_quotes_ai\combined\codes.json"
        
        # Load the codes data
        with open(codes_file_path, 'r') as f:
            codes_data = json.load(f)
            
        # Get codes associated with selected themes
        theme_codes = []
        for theme in selected_themes:
            theme_codes.extend([
                code['code'] 
                for code in codes_data 
                if code['theme'] == theme
            ])
            
        # Load and filter the categorized quotes
        themed_quotes = []
        with jsonlines.open(categorized_quotes_path) as reader:
            for quote in reader:
                # Check if any of the quote's codes match our theme codes
                if any(code in theme_codes for code in quote.get('codes', [])):
                    # Add theme information to the quote
                    quote['themes'] = [
                        theme for theme in selected_themes
                        if any(
                            code['code'] in quote.get('codes', [])
                            for code in codes_data
                            if code['theme'] == theme
                        )
                    ]
                    themed_quotes.append(quote)
        
        # Group quotes by theme
        quotes_by_theme = {theme: [] for theme in selected_themes}
        for quote in themed_quotes:
            for theme in quote['themes']:
                quotes_by_theme[theme].append(quote)
        
        return jsonify({
            'status': 'success',
            'quotes_by_theme': quotes_by_theme,
            'total_quotes': len(themed_quotes),
            'themes': selected_themes,
            'codes': theme_codes
        })
        
    except Exception as e:
        logger.error(f"Error fetching theme quotes: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/get_related_subreddits', methods=['POST'])
def get_related_subreddits():
    data = request.json
    topic = data.get('topic')
    related_subreddits = get_relevant_subreddits(topic)
    return jsonify({'related_subreddits': related_subreddits})

@app.route('/api/start-processing', methods=['POST'])
def start_processing():
    """Start the processing pipeline"""
    if processing_status['is_processing']:
        return jsonify({
            'status': 'error',
            'message': 'Processing is already running'
        }), 400

    Thread(target=run_processing_pipeline).start()
    return jsonify({
        'status': 'success',
        'message': 'Processing started'
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current processing status"""
    return jsonify(processing_status)

@app.route('/api/results', methods=['GET'])
def get_results():
    """Get the final analysis results"""
    try:
        analysis_file_path = r"C:\Users\mwang\PolicyPulse\output_quotes_ai\combined\summary_analysis.json"
        
        if not os.path.exists(analysis_file_path):
            return jsonify({
                'status': 'error',
                'message': 'Analysis file not found'
            }), 404

        with open(analysis_file_path, 'r') as f:
            analysis_data = json.load(f)

        return jsonify(analysis_data)

    except Exception as e:
        logger.error(f"Error reading analysis file: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Your existing helper function for getting subreddits
def get_relevant_subreddits(topic):
    relevant_subreddits = []
    chunk_size = 200
    
    for i in range(0, len(subreddits), chunk_size):
        subreddits_chunk = subreddits[i:i + chunk_size]
        prompt = f"Here is a list of subreddits: {subreddits_chunk}. Based on the topic '{topic}', please provide a list of the most relevant subreddits from the list. If there are multiple relevant subreddits, separate their names with commas. If none are relevant, respond with a blank line."
        
        response = openai.chat.completions.create(
            model=deployment_name,
            messages=[{"role": "user", "content": prompt}]
        )
        
        if response.choices and response.choices[0].message.content:
            responses = response.choices[0].message.content.split(",")
            for r in responses:
                relevant_subreddits.append(r)

    return relevant_subreddits

if __name__ == "__main__":
    # Load the CSV file with subreddits
    subreddits = pd.read_csv("data/subreddits.csv")['name'].tolist()
    app.run(host='0.0.0.0', port=5050, debug=True)