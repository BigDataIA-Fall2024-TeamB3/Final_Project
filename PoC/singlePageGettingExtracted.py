from serpapi import GoogleSearch
import json
import os
from datetime import datetime
import time

def extract_jobs_data(api_key, num_pages=3):
    all_jobs = []
    
    for page in range(num_pages):
        # Parameters for the API request
        params = {
            'api_key': api_key,                           # Your API key
            'engine': 'google_jobs',                      # Search engine
            'q': 'software engineer',                     # Search query
            'hl': 'en',                                  # Language
            'gl': 'us',                                  # Country
            'google_domain': 'google.com',               # Google domain
            'start': page * 10 if page > 0 else None,    # Pagination
        }
        
        try:
            # Make the API request
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Check if we have job results and it's not empty
            if 'jobs_results' not in results or not results['jobs_results']:
                print(f"No more results found on page {page + 1}")
                break
            
            # Extract specific parameters from each job
            for job in results['jobs_results']:
                job_data = {
                    'title': job.get('title', 'N/A'),
                    'company': job.get('company_name', 'N/A'),
                    'location': job.get('location', 'N/A'),
                    'description': job.get('description', 'N/A')[:500] + '...' if job.get('description') else 'N/A',
                    'via': job.get('via', 'N/A'),
                    'posted_at': job.get('detected_extensions', {}).get('posted_at', 'N/A'),
                    'schedule_type': job.get('detected_extensions', {}).get('schedule_type', 'N/A'),
                    'salary': job.get('detected_extensions', {}).get('salary', 'N/A'),
                    'benefits': [ext for ext in job.get('extensions', []) if 'insurance' in ext.lower() or 'benefit' in ext.lower()],
                    'apply_link': job.get('apply_options', [{}])[0].get('link', 'N/A') if job.get('apply_options') else 'N/A'
                }
                all_jobs.append(job_data)
                
            print(f"Processed page {page + 1} - Found {len(results['jobs_results'])} jobs")
            
            # Get next page token if available
            if 'serpapi_pagination' in results and 'next_page_token' in results['serpapi_pagination']:
                params['next_page_token'] = results['serpapi_pagination']['next_page_token']
            else:
                break  # No more pages available
                
            # Add a small delay between requests
            time.sleep(2)
            
        except Exception as e:
            print(f"Error processing page {page + 1}: {str(e)}")
            continue
    
    return all_jobs

def save_to_json(jobs_data, filename='software_engineer_jobs.json'):
    """Save the extracted jobs data to a JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(jobs_data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(jobs_data)} jobs to {filename}")

def main():
    # Your SerpApi key
    API_KEY = "73565b3ac23767a39bca23cd60d7e6f29085e8e4ca32c71bcf5f799a59d3d8c6"
    
    try:
        # Extract jobs data
        print("Starting job extraction...")
        jobs_data = extract_jobs_data(API_KEY)
        
        if not jobs_data:
            print("No jobs were found!")
            return
            
        # Save to JSON file
        save_to_json(jobs_data)
        
        # Print summary
        print(f"\nExtraction completed successfully!")
        print(f"Total jobs extracted: {len(jobs_data)}")
        
        # Print sample of first job
        if jobs_data:
            print("\nSample of first job entry:")
            first_job = jobs_data[0]
            for key, value in first_job.items():
                if key == 'description':
                    print(f"{key}: {value[:150]}...")  # Show first 150 chars of description
                else:
                    print(f"{key}: {value}")
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()