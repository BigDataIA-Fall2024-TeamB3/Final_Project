from serpapi import GoogleSearch
import json
import csv
import os
from datetime import datetime, timedelta
import time
import re

def extract_days_ago(posted_at):
    """Extract number of days from posted_at string"""
    if not posted_at or posted_at == 'N/A':
        return None
        
    # Extract numbers using regex
    match = re.search(r'(\d+)', posted_at)
    if match:
        days = int(match.group(1))
        if 'month' in posted_at.lower():
            days = days * 30  # Approximate month to days
        elif 'week' in posted_at.lower():
            days = days * 7   # Convert weeks to days
        return days
    elif 'hour' in posted_at.lower() or 'today' in posted_at.lower():
        return 0
    return None

def extract_time_info(posted_at):
    """
    Extract time information from posted_at string
    Returns tuple of (number, unit)
    """
    if not posted_at or posted_at == 'N/A':
        return None, None
    
    # Extract numbers using regex
    match = re.search(r'(\d+)\s*(\w+)', posted_at.lower())
    if not match:
        return None, None
        
    number = int(match.group(1))
    unit = match.group(2).rstrip('s')  # remove plural 's' if present
    
    return number, unit

def calculate_posted_date(posted_at):
    """
    Calculate actual posted date from time ago format
    Keeps same date for hours, changes date for days/weeks/months
    """
    if not posted_at or posted_at == 'N/A':
        return 'N/A'
    
    number, unit = extract_time_info(posted_at)
    if not number or not unit:
        return 'N/A'
    
    today = datetime.now()
    
    # Handle different time units
    if 'hour' in unit:
        # For hours, keep today's date
        return today.strftime('%Y-%m-%d')
    elif 'day' in unit:
        posted_date = today - timedelta(days=number)
    elif 'week' in unit:
        posted_date = today - timedelta(days=number * 7)
    elif 'month' in unit:
        posted_date = today - timedelta(days=number * 30)  # approximate
    else:
        return 'N/A'
    
    return posted_date.strftime('%Y-%m-%d')

def extract_jobs_for_title(api_key, job_title, num_pages=3):
    all_jobs = []
    current_page = 1
    next_page_token = None
    
    while current_page <= num_pages:
        params = {
            'api_key': api_key,                  
            'engine': 'google_jobs',             
            'q': job_title,            
            'hl': 'en',                         
            'gl': 'us',                         
            'google_domain': 'google.com'        
        }
        
        if next_page_token:
            params['next_page_token'] = next_page_token
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if 'jobs_results' not in results or not results['jobs_results']:
                print(f"No more results found on page {current_page} for {job_title}")
                break
            
            jobs_on_this_page = results['jobs_results']
            print(f"Found {len(jobs_on_this_page)} jobs on page {current_page} for {job_title}")
            
            for job in jobs_on_this_page:
                apply_links = []
                if job.get('apply_options'):
                    for option in job['apply_options']:
                        if option.get('link'):
                            apply_links.append(f"{option.get('title', 'Unknown')}: {option.get('link')}")
                
                posted_at = job.get('detected_extensions', {}).get('posted_at', 'N/A')
                posted_date = calculate_posted_date(posted_at)
                
                job_data = {
                    'search_query': job_title,
                    'title': job.get('title', 'N/A'),
                    'company': job.get('company_name', 'N/A'),
                    'location': job.get('location', 'N/A'),
                    'description': job.get('description', 'N/A')[:500] + '...' if job.get('description') else 'N/A',
                    'posted_at': posted_at,
                    'posted_date': posted_date,
                    'apply_links': ' | '.join(apply_links) if apply_links else 'N/A'
                }
                all_jobs.append(job_data)
            
            print(f"Successfully processed page {current_page} for {job_title} - Total jobs so far: {len(all_jobs)}")
            
            serpapi_pagination = results.get('serpapi_pagination', {})
            next_page_token = serpapi_pagination.get('next_page_token')
            
            if not next_page_token:
                print(f"No next page token found after page {current_page} for {job_title}")
                break
                
            current_page += 1
            time.sleep(2)
            
        except Exception as e:
            print(f"Error processing page {current_page} for {job_title}: {str(e)}")
            break
    
    return all_jobs

def save_to_csv(jobs_data, filename='tech_jobs.csv'):
    """Save the extracted jobs data to a CSV file"""
    fieldnames = ['search_query', 'title', 'company', 'location', 'description', 'posted_at', 'posted_date', 'apply_links']
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(jobs_data)
        print(f"\nSuccessfully saved {len(jobs_data)} jobs to {filename}")
        
    except Exception as e:
        print(f"Error saving to CSV: {str(e)}")

def save_to_json(jobs_data, filename='tech_jobs.json'):
    """Save the extracted jobs data to a JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(jobs_data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(jobs_data)} jobs to {filename}")

def main():
    API_KEY = "your key"
    
    job_titles = [
        'software engineer',
        'data engineer',
        'data scientist'
    ]
    
    try:
        all_jobs = []
        
        print("Starting job extraction...")
        for job_title in job_titles:
            print(f"\nSearching for {job_title} positions...")
            jobs = extract_jobs_for_title(API_KEY, job_title)
            all_jobs.extend(jobs)
            print(f"Found {len(jobs)} {job_title} positions")
            time.sleep(3)
        
        if not all_jobs:
            print("No jobs were found!")
            return
            
        save_to_json(all_jobs)
        save_to_csv(all_jobs)
        
        print(f"\nExtraction completed successfully!")
        print(f"Total jobs extracted: {len(all_jobs)}")
        
        # Print summary by job title
        for job_title in job_titles:
            count = len([job for job in all_jobs if job['search_query'] == job_title])
            print(f"- {job_title}: {count} positions")
        
        # Print sample entry
        if all_jobs:
            print("\nSample job entry with actual posted date:")
            first_job = all_jobs[0]
            for key, value in first_job.items():
                if key == 'description':
                    print(f"{key}: {value[:150]}...")
                else:
                    print(f"{key}: {value}")
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()