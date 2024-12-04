from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the directory containing your scripts to the Python path
dag_folder = os.path.dirname(os.path.abspath(__file__))
sys.path.append(dag_folder)

# Import functions from your scripts
from multijob_transformed import extract_jobs_for_title, save_to_csv, save_to_json
from upload_table import update_snowflake_from_csv

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
        'data scientist',
        'machine learning engineer',
        'AI Engineer',
        'data analyst',
        'AI/ML Engineer',
        'DevOps Engineer',
        'full stack engineer'
    ]
    
    try:
        all_jobs = []
        print("Starting job extraction...")
        
        for job_title in job_titles:
            print(f"\nSearching for {job_title} positions...")
            jobs = extract_jobs_for_title(API_KEY, job_title, 30)
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

def upload_to_snowflake():
    """Function to upload CSV data to Snowflake"""
    try:
        csv_path = '/opt/airflow/data/tech_jobs.csv'
        print(f"Starting Snowflake upload from {csv_path}")
        update_snowflake_from_csv(csv_path)
        print("Snowflake upload completed successfully")
    except Exception as e:
        print(f"Error uploading to Snowflake: {str(e)}")
        raise e

# Create the DAG
with DAG(
    'job_scraping_and_upload_dag',
    default_args=default_args,
    description='DAG for scraping job listings and uploading to Snowflake',
    schedule_interval=timedelta(days=1),  # Run daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['job_scraping', 'snowflake'],
) as dag:
    
    # Task 1: Scrape jobs and save to CSV
    scrape_jobs_task = PythonOperator(
        task_id='scrape_jobs',
        python_callable=scrape_and_save_jobs,
        dag=dag,
    )
    
    # Task 2: Upload CSV to Snowflake
    upload_to_snowflake_task = PythonOperator(
        task_id='upload_to_snowflake',
        python_callable=upload_to_snowflake,
        dag=dag,
    )
    
    # Set task dependencies
    scrape_jobs_task >> upload_to_snowflake_task  # Run scraping first, then upload