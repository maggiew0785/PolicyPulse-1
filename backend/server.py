from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv
import pandas as pd 
import json
from threading import Thread
import logging
import traceback
from data.steps.a_reddit_to_quotes import main as reddit_quotes_main
from data.steps.b_json_to_subtopics import main as subtopics_main
from data.steps.c_subtopic_codes_to_quotes import main as assign_codes_main

# Load environment variables
load_dotenv()

def get_project_root():
    """Get the path to the PolicyPulse project root directory"""
    current = os.path.dirname(os.path.abspath(__file__))
    while os.path.basename(current) != "PolicyPulse":
        current = os.path.dirname(current)
        if not current or current == os.path.dirname(current):  # Reached root without finding PolicyPulse
            raise Exception("Could not find PolicyPulse root directory")
    return current

base_dir = os.path.dirname(os.path.abspath(__file__))
system_prompt_path = os.path.join(base_dir, "..", "prompts", "b_analyze_summaries_prompt.txt")
template_dir = os.path.abspath('../frontend/build')  # Points to where index.html is
static_dir = os.path.abspath('../frontend/static')   # Points to where main.js and main.css are

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

class ProjectPaths:
    """Centralized path configuration for the project"""
    def __init__(self):
        self.root = get_project_root()
        
        # Directory paths
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.input_dir = os.path.join(self.root, "output", "output_raw_ai")
        self.output_dir = os.path.join(self.root, "output", "output_quotes_ai")
        self.frontend_dir = os.path.join(self.root, "frontend")
        self.prompts_dir = os.path.join(self.root, "prompts")
        
        # Frontend specific paths
        self.template_dir = os.path.join(self.frontend_dir, "build")
        self.static_dir = os.path.join(self.frontend_dir, "static")
        
        # Output specific paths
        self.combined_file = None  # Initialize as None
        self.quotes_file = None 
        self.analysis_file = None 

        # Create necessary directories
        self.create_directories()
    
    def create_directories(self):
        """Create all necessary directories if they don't exist"""
        directories = [
            self.input_dir,
            self.output_dir,
        ]
        for directory in directories:
            if directory:  # Only create if not None
                os.makedirs(directory, exist_ok=True)

# Create a single instance to use throughout the application
paths = ProjectPaths()

# Initialize Flask with the correct paths
app = Flask(__name__, 
    static_folder=paths.static_dir, 
    template_folder=paths.template_dir)
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

# At the top of your server.py file, define the global state
processing_state = {
    'is_processing': False,
    'current_stage': None,
    'subreddit': None,
    'theme': None,
    'error': None,
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_related_subreddits', methods=['POST'])
def get_related_subreddits():
    data = request.json
    topic = data.get('topic')
    related_subreddits = get_relevant_subreddits(topic)
    return jsonify({'related_subreddits': related_subreddits})

@app.route('/get_themes/<subreddit>', methods=['GET'])
def get_themes(subreddit):
    paths.combined_file = os.path.join(paths.output_dir, f"r_{subreddit}", "combined_quotes.jsonl")
    print(f"Requested subreddit: {subreddit}")  # Log the received subreddit
    # Create a prompt for the OpenAI API
    prompt = f"Generate a list of 9 themes that policymakers and policy researchers would be interested in learning more about, related to the subreddit '{subreddit}', each with a title ('title') and a very brief description ('description'). Return the themes in JSON format."

    # Call the OpenAI API to get themes
    try:
        response = openai.chat.completions.create(
            model=deployment_name,  # Specify your model
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        # print(response)
        

        # Extract the content from the response
        themes_json = response.choices[0].message.content.strip()
        # print(themes_json)

        # Extract only the JSON part by removing the Markdown formatting
        # Assuming the JSON is wrapped in ```json ... ```
        json_start = themes_json.find("[")  # Find the start of the JSON array
        json_end = themes_json.rfind("]") + 1  # Find the end of the JSON array
        clean_json_string = themes_json[json_start:json_end]

        # Print the cleaned JSON string for debugging
        # print("Cleaned JSON String:", clean_json_string)

        # Parse the cleaned JSON string to a Python dictionary
        themes_data = json.loads(clean_json_string)

        # Return the JSON response
        return jsonify(themes_data)

    except Exception as e:
        print(f"Error fetching themes: {e}")
        return jsonify({"error": "Failed to retrieve themes."}), 500

@app.route('/api/start-processing', methods=['POST'])
def start_processing():
    global processing_state

    try:
        print("Received start-processing request")
        data = request.json
        print(f"Request data: {data}")
        
        subreddit = data.get('subreddit')
        theme = data.get('theme')
        
        print(f"Subreddit: {subreddit}")
        print(f"Theme: {theme}")

        if not subreddit or not theme:
            return jsonify({'error': 'Subreddit and theme are required'}), 400

        if processing_state['is_processing']:
            return jsonify({'error': 'Processing already in progress'}), 429

        # Clean the paths and create directories
        clean_subreddit = subreddit.replace('r/', '')
        clean_theme = theme.replace(' ', '_')
        output_subdir = os.path.join(paths.output_dir, f"r_{clean_subreddit}", clean_theme)
        
        try:
            os.makedirs(output_subdir, exist_ok=True)
            print(f"Created output directory: {output_subdir}")
        except Exception as e:
            print(f"Error creating directories: {e}")
            return jsonify({'error': f'Failed to create output directories: {str(e)}'}), 500

        # Update processing state
        processing_state.update({
            'is_processing': True,
            'current_stage': 'reddit_quotes',
            'subreddit': subreddit,
            'theme': theme,
            'error': None
        })

        # Build prompt parameters
        prompt_params = {
            'subreddit': subreddit,
            'topic': clean_subreddit,
            'theme': theme,
            'theme_focus': theme.lower(),
            'concerns_scope': f"{theme.lower()} in the context of {clean_subreddit}"
        }

        print("Starting processing thread with parameters:", prompt_params)

        # Start processing in a thread
        thread = Thread(target=process_in_background, args=(subreddit, theme, prompt_params))
        thread.daemon = True
        thread.start()

        return jsonify({'status': 'Processing started', 'output_dir': output_subdir})

    except Exception as e:
        print(f"Error in start_processing: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        processing_state['error'] = str(e)
        processing_state['is_processing'] = False
        return jsonify({'error': str(e)}), 500
    
# def run_processing_pipeline():
#     """Run both processing scripts in sequence"""
#     try:
#         # Start reddit quotes collection
#         processing_status.update({
#             'is_processing': True,
#             'current_stage': 'reddit_quotes',
#             'error': None,
#             'progress': 0
#         })
        
#         # Define input and output directories using os.path.join
#         base_dir = os.path.dirname(os.path.abspath(__file__))
#         input_directory = os.path.join(base_dir, "..", "output", "output_raw_ai")
#         output_directory = os.path.join(base_dir, "..", "output", "output_quotes_ai")

#         print("input_directory", input_directory)
#         print(output_directory)
        
#         # Ensure directories exist
#         os.makedirs(input_directory, exist_ok=True)
#         os.makedirs(output_directory, exist_ok=True)
        
#         # Start reddit quotes collection
#         logger.info("Starting Reddit data collection...")
#         reddit_quotes_main(input_directory, output_directory)
#         processing_status['progress'] = 50
        
#         # Start subtopics generation
#         processing_status['current_stage'] = 'subtopics'
#         print("STARTING TO GO TO STEP 3")
#         logger.info("Starting subtopics analysis...")
        
#         # Check if `subtopics_main` requires arguments
#         subtopics_main()  # Pass directories if required
#         processing_status['progress'] = 75
        
#         # Call assign_codes_main if required
#         assign_codes_main()  # Verify if arguments are needed
#         processing_status['progress'] = 100
        
#         logger.info("Processing completed successfully")
        
#     except Exception as e:
#         processing_status['error'] = str(e)
#         logger.error(f"Error during processing: {e}")
#         traceback.print_exc()
        
#     finally:
#         processing_status.update({
#             'is_processing': False,
#             'current_stage': None
#         })

import jsonlines
@app.route('/api/quotes/<subtopic>')
def get_quotes(subtopic):
    try:
        print(f"Fetching quotes for subtopic: {subtopic}")

        if not os.path.exists(paths.quotes_file):
            print(f"Quotes file not found: {paths.quotes_file}")
            return jsonify({'error': 'Quotes file not found'}), 404

        matching_quotes = []
        with jsonlines.open(paths.quotes_file) as reader:
            for quote in reader:
                if any(code['code_name'] == subtopic for code in quote.get('codes', [])):
                    matching_quotes.append({
                        'text': quote.get('quote', ''),
                        'summary': quote.get('summary', ''),  # Add this line
                        'subreddit': quote.get('source_id', ''),
                        'score': quote.get('score', 0)
                    })

        print(f"Found {len(matching_quotes)} matching quotes for subtopic: {subtopic}")
        return jsonify(matching_quotes[:5])

    except Exception as e:
        print(f"Error fetching quotes: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to fetch quotes: {str(e)}'}), 500

def process_data(subreddit: str, theme: str, prompt_params: dict):
    global processing_state
    try:
        processing_state['current_stage'] = 'reddit_quotes'

        # Clean the names but don't create the full path yet
        clean_subreddit = subreddit.replace('r/', '').replace('/', '_')
        clean_theme = theme.replace(' ', '_')
        
        print(f"Starting processing with cleaned names:")
        print(f"Subreddit: {clean_subreddit}")
        print(f"Theme: {clean_theme}")

        # Let process_quotes create and return the proper directory structure
        from data.steps.a_reddit_to_quotes import main as process_quotes
        output_subdir = process_quotes(paths.input_dir, paths.output_dir, clean_subreddit, theme, prompt_params)
        
        print(f"Received output directory from process_quotes: {output_subdir}")

        # Check if quotes were generated
        combined_file = os.path.join(output_subdir, 'combined_quotes.jsonl')
        if not os.path.exists(combined_file) or os.path.getsize(combined_file) == 0:
            raise NoQuotesFoundError(f"No relevant quotes found for subreddit '{subreddit}' and theme '{theme}'")

        # Count number of quotes
        quote_count = 0
        with open(combined_file, 'r') as f:
            for line in f:
                if line.strip():  # Check if line is not empty
                    quote_count += 1
        
        if quote_count == 0:
            raise NoQuotesFoundError(f"No relevant quotes found for subreddit '{subreddit}' and theme '{theme}'")

        print(f"Found {quote_count} quotes to process")
        if quote_count > 0:
            # Update the global paths using the directory returned by process_quotes
            paths.quotes_file = os.path.join(output_subdir, "categorized_quotes.jsonl")
            paths.analysis_file = os.path.join(output_subdir, "summary_analysis.json")
            
            print(f"Set paths to:")
            print(f"Quotes file: {paths.quotes_file}")
            print(f"Analysis file: {paths.analysis_file}")

            # Process subtopics using the same directory
            processing_state['current_stage'] = 'subtopics'
            from data.steps.b_json_to_subtopics import main as process_subtopics
            process_subtopics(output_subdir)

            # Process codes using the same directory
            from data.steps.c_subtopic_codes_to_quotes import main as process_codes
            process_codes(output_subdir)

            # Verify files exist and have content
            if not os.path.exists(paths.quotes_file) or os.path.getsize(paths.quotes_file) == 0:
                raise NoQuotesFoundError("No quotes were generated in the final processing step")
                
            if not os.path.exists(paths.analysis_file) or os.path.getsize(paths.analysis_file) == 0:
                raise ProcessingError("Analysis file was not created or is empty")

            # Mark completion
            processing_state['current_stage'] = 'complete'
            processing_state['is_processing'] = False
        
    except NoQuotesFoundError as e:
        print(f"No quotes found: {str(e)}")
        processing_state.update({
            'error': str(e),
            'is_processing': False,
            'current_stage': 'failed'
        })
        # Clean up any partial output
        if 'output_subdir' in locals():
            try:
                import shutil
                shutil.rmtree(output_subdir)
                print(f"Cleaned up output directory: {output_subdir}")
            except Exception as cleanup_error:
                print(f"Error cleaning up directory: {cleanup_error}")
        return  # Ensure we stop processing here
    
    except Exception as e:
        print(f"Error in process_data: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        processing_state['error'] = str(e)
        processing_state['is_processing'] = False
        processing_state['current_stage'] = 'failed'

# Custom exceptions for better error handling
class NoQuotesFoundError(Exception):
    """Raised when no relevant quotes are found during processing"""
    pass

class ProcessingError(Exception):
    """Raised when there's an error in the processing pipeline"""
    pass

# Update the process_in_background function to handle the new exceptions
def process_in_background(subreddit, theme, prompt_params):
    try:
        process_data(subreddit, theme, prompt_params)
    except NoQuotesFoundError as e:
        logger.error(f"No quotes found: {str(e)}")
        processing_state.update({
            'error': str(e),
            'is_processing': False,
            'current_stage': 'failed'
        })
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        processing_state['error'] = str(e)
        processing_state['is_processing'] = False
        processing_state['current_stage'] = 'failed'


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current processing status"""
    status_data = {
        'is_processing': processing_state['is_processing'],
        'current_stage': processing_state['current_stage'],
        'error': processing_state['error'],
        'quotes_file': paths.quotes_file,
        'analysis_file': paths.analysis_file,
        'quotes_file_exists': paths.quotes_file and os.path.exists(paths.quotes_file),
        'analysis_file_exists': paths.analysis_file and os.path.exists(paths.analysis_file)
    }
    
    print(f"Status check - Current paths:")
    print(f"Quotes file: {paths.quotes_file}")
    print(f"Analysis file: {paths.analysis_file}")
    
    return jsonify(status_data)


@app.route('/api/results', methods=['GET'])
def get_results():
    try:
        print("Checking for analysis file...")
        print(f"Current paths.analysis_file value: {paths.analysis_file}")
        
        if paths.analysis_file is None:
            return jsonify({
                'status': 'error',
                'message': 'Analysis file path not set'
            }), 500
            
        if not os.path.exists(paths.analysis_file):
            print(f"Analysis file not found at: {paths.analysis_file}")
            return jsonify({
                'status': 'error',
                'message': f'Analysis file not found at {paths.analysis_file}'
            }), 404

        print(f"Found analysis file, attempting to read from: {paths.analysis_file}")
        
        try:
            with open(paths.analysis_file, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
                print("Successfully loaded analysis data")
                print(f"Data contents: {json.dumps(analysis_data, indent=2)}")
        except json.JSONDecodeError as je:
            print(f"JSON decode error: {str(je)}")
            return jsonify({
                'status': 'error',
                'message': f'Invalid JSON in analysis file: {str(je)}'
            }), 500
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Error reading analysis file: {str(e)}'
            }), 500

        return jsonify(analysis_data)
    
    except Exception as e:
        print(f"Unexpected error in get_results: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }), 500
    
@app.route('/api/download-quotes', methods=['GET'])
def download_quotes():
    try:
        if not paths.quotes_file or not os.path.exists(paths.quotes_file):
            return jsonify({
                'status': 'error',
                'message': 'Quotes file not found'
            }), 404

        # Read all quotes from the JSONL file
        quotes = []
        with open(paths.quotes_file, 'r', encoding='utf-8') as f:
            for line in f:
                quotes.append(json.loads(line))

        return jsonify({
            'status': 'success',
            'data': quotes
        })

    except Exception as e:
        print(f"Error downloading quotes: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
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