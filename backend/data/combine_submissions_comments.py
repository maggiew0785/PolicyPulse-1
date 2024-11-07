import os
import json
import csv
from collections import defaultdict
from tqdm import tqdm

import os

def process_subreddit(submissions_file, comments_file, output_folder):
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Proceed with combining data and writing to CSV
    submissions = read_submissions(submissions_file)
    comments = read_comments(comments_file)

    # Combine submissions and comments
    combined_data = {}

    for submission_id, submission in submissions.items():
        combined_data[submission_id] = {
            'id': submission_id,
            'title': submission['title'],
            'selftext': submission['selftext'],
            'body': ' '.join(comments.get(submission_id, []))
        }

    # Process comments without matching submissions
    for comment_id in comments:
        if comment_id not in combined_data:
            combined_data[comment_id] = {
                'id': comment_id,
                'title': '',
                'selftext': '',
                'body': ' '.join(comments[comment_id])
            }

    # Specify the output file path
    output_file = os.path.join(output_folder, "combined_data.csv")
    
    # Write combined data to output file
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'title', 'selftext', 'body'])
        for data in combined_data.values():
            if is_valid_content(data['selftext']) or is_valid_content(data['body']):
                writer.writerow([
                    data['id'],
                    data['title'],
                    data['selftext'],
                    data['body']
                ])

def read_submissions(file_path):
    submissions = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)  # Parse each line as JSON
                submission_id = data['id']  # Get the unique submission ID
                submissions[submission_id] = {
                    'title': data.get('title', ''),
                    'selftext': data.get('selftext', '') if is_valid_content(data.get('selftext', '')) else ''
                }
            except json.JSONDecodeError as e:
                print(f"Error reading line in {file_path}: {str(e)}")
    return submissions

def read_comments(file_path):
    comments = defaultdict(list)
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)  # Parse each line as JSON
                submission_id = data['link_id'][3:]  # Remove 't3_' prefix to get the ID
                if is_valid_content(data.get('body', '')):
                    comments[submission_id].append(data['body'])
            except json.JSONDecodeError as e:
                print(f"Error reading line in {file_path}: {str(e)}")
    return comments

def is_valid_content(text):
    if text in ['[removed]', '[deleted]', ''] or text is None:
        return False
    return len(text.split()) >= 5

                
import argparse


# python combine_submissions_comments.py "C:\\Users\\mwang\\PolicyPulse\\ArtificialInteligence_submissions" "C:\\Users\\mwang\\PolicyPulse\\ArtificialInteligence_comments" "C:\\Users\\mwang\\PolicyPulse\\output_raw_ai"

def main():
    parser = argparse.ArgumentParser(description="Process subreddit data")
    parser.add_argument("submissions_file", help="Path to the submissions file")
    parser.add_argument("comments_file", help="Path to the comments file")
    parser.add_argument("output_folder", help="Path to the folder where output files will be saved")
    args = parser.parse_args()
    
    process_subreddit(args.submissions_file, args.comments_file, args.output_folder)

if __name__ == "__main__":
    main()
