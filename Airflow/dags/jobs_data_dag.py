from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the directory containing your script to the Python path
# Assuming your script is in the dags folder
dag_folder = os.path.dirname(os.path.abspath(__file__))
sys.path.append(dag_folder)

# Import functions from your script
from multijob_transformed import extract_jobs_for_title, save_to_csv, save_to_json

# Define default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def scrape_and_save_jobs():
    """Function to execute the job scraping process"""
    API_KEY = os.getenv("SERP_API_KEY")
    job_titles = [
        'software engineer',
        'data engineer',
    ]
    
    try:
        all_jobs = []
        
        print("Starting job extraction...")
        for job_title in job_titles:
            print(f"\nSearching for {job_title} positions...")
            jobs = extract_jobs_for_title(API_KEY, job_title, 5)
            all_jobs.extend(jobs)
            print(f"Found {len(jobs)} {job_title} positions")
        
        if not all_jobs:
            print("No jobs were found!")
            return
        
        # Save files in the data directory
        data_dir = '/opt/airflow/data'
        os.makedirs(data_dir, exist_ok=True)
        
        json_path = os.path.join(data_dir, 'tech_jobs.json')
        csv_path = os.path.join(data_dir, 'tech_jobs.csv')
        
        save_to_json(all_jobs, json_path)
        save_to_csv(all_jobs, csv_path)
        
        print(f"\nExtraction completed successfully!")
        print(f"Total jobs extracted: {len(all_jobs)}")
        
        # Print summary by job title
        for job_title in job_titles:
            count = len([job for job in all_jobs if job['search_query'] == job_title])
            print(f"- {job_title}: {count} positions")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise e

# Create the DAG
with DAG(
    'job_scraping_dag',
    default_args=default_args,
    description='DAG for scraping job listings using SerpAPI',
    schedule_interval=timedelta(days=1),  # Run daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['job_scraping'],
) as dag:

    # Create PythonOperator to run the scraping task
    scrape_jobs_task = PythonOperator(
        task_id='scrape_jobs',
        python_callable=scrape_and_save_jobs,
        dag=dag,
    )

    # Set task dependencies (only one task in this case)
    scrape_jobs_task