from serpapi import GoogleSearch
import json
import csv
import os
from datetime import datetime
import time

def extract_jobs_data(api_key, num_pages=3):
    all_jobs = []
    current_page = 1
    next_page_token = None
    
    while current_page <= num_pages:
        # Parameters for the API request
        params = {
            'api_key': api_key,                  
            'engine': 'google_jobs',             
            'q': 'software engineer',            
            'hl': 'en',                         
            'gl': 'us',                         
            'google_domain': 'google.com'        
        }
        
        # Add next_page_token if we have one (for pages after first)
        if next_page_token:
            params['next_page_token'] = next_page_token
        
        try:
            # Make the API request
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Check if we have job results and it's not empty
            if 'jobs_results' not in results or not results['jobs_results']:
                print(f"No more results found on page {current_page}")
                break
            
            # Extract jobs from current page
            jobs_on_this_page = results['jobs_results']
            print(f"Found {len(jobs_on_this_page)} jobs on page {current_page}")
            
            # Extract specific parameters from each job
            for job in jobs_on_this_page:
                # Get all apply links if available
                apply_links = []
                if job.get('apply_options'):
                    for option in job['apply_options']:
                        if option.get('link'):
                            apply_links.append(f"{option.get('title', 'Unknown')}: {option.get('link')}")
                
                job_data = {
                    'title': job.get('title', 'N/A'),
                    'company': job.get('company_name', 'N/A'),
                    'location': job.get('location', 'N/A'),
                    'description': job.get('description', 'N/A')[:500] + '...' if job.get('description') else 'N/A',
                    'posted_at': job.get('detected_extensions', {}).get('posted_at', 'N/A'),
                    'apply_links': ' | '.join(apply_links) if apply_links else 'N/A'
                }
                all_jobs.append(job_data)
            
            print(f"Successfully processed page {current_page} - Total jobs so far: {len(all_jobs)}")
            
            # Check for next page token
            serpapi_pagination = results.get('serpapi_pagination', {})
            next_page_token = serpapi_pagination.get('next_page_token')
            
            if not next_page_token:
                print(f"No next page token found after page {current_page}")
                break
                
            current_page += 1
            time.sleep(2)  # Small delay between requests
            
        except Exception as e:
            print(f"Error processing page {current_page}: {str(e)}")
            break
    
    return all_jobs

def save_to_csv(jobs_data, filename='software_engineer_jobs.csv'):
    """Save the extracted jobs data to a CSV file"""
    # Define the fieldnames for the CSV
    fieldnames = ['title', 'company', 'location', 'description', 'posted_at', 'apply_links']
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write the header
            writer.writeheader()
            
            # Write the job data
            for job in jobs_data:
                writer.writerow(job)
                
        print(f"\nSuccessfully saved {len(jobs_data)} jobs to {filename}")
        
    except Exception as e:
        print(f"Error saving to CSV: {str(e)}")

def save_to_json(jobs_data, filename='software_engineer_jobs.json'):
    """Save the extracted jobs data to a JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(jobs_data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(jobs_data)} jobs to {filename}")

def main():
    # Your SerpApi key
    API_KEY = "your key"
    
    try:
        # Extract jobs data
        print("Starting job extraction...")
        jobs_data = extract_jobs_data(API_KEY, num_pages=3)
        
        if not jobs_data:
            print("No jobs were found!")
            return
            
        # Save to both JSON and CSV
        save_to_json(jobs_data)
        save_to_csv(jobs_data)
        
        # Print summary
        print(f"\nExtraction completed successfully!")
        print(f"Total jobs extracted: {len(jobs_data)}")
        
        # Print sample of first job
        if jobs_data:
            print("\nSample of first job entry:")
            first_job = jobs_data[0]
            for key, value in first_job.items():
                if key == 'description':
                    print(f"{key}: {value[:150]}...")
                else:
                    print(f"{key}: {value}")
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()