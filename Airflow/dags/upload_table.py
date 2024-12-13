import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from dotenv import load_dotenv
import os

def update_snowflake_from_csv(csv_file='tech_jobs.csv'):
    """
    Update Snowflake table with data from CSV file.
    - First deletes all existing data
    - Then uploads new data with proper column mapping
    """
    try:
        # Load environment variables
        load_dotenv()
        
        # Get Snowflake credentials from environment variables
        snowflake_user = os.getenv('SNOWFLAKE_USER')
        snowflake_password = os.getenv('SNOWFLAKE_PASSWORD')
        snowflake_account = os.getenv('SNOWFLAKE_ACCOUNT')
        snowflake_warehouse = os.getenv('SNOWFLAKE_WAREHOUSE')
        snowflake_database = os.getenv('SNOWFLAKE_JOBSDB')
        snowflake_schema = os.getenv('SNOWFLAKE_SCHEMA')
        #snowflake_role = os.getenv('SNOWFLAKE_ROLE')
        snowflake_role = 'ACCOUNTADMIN'
        
        # Verify all required environment variables are present
        required_vars = [
            'SNOWFLAKE_USER', 'SNOWFLAKE_PASSWORD', 'SNOWFLAKE_ACCOUNT',
            'SNOWFLAKE_WAREHOUSE', 'SNOWFLAKE_JOBSDB', 'SNOWFLAKE_SCHEMA'
            #,'SNOWFLAKE_ROLE'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
        
        # Read CSV file
        print(f"Reading CSV file: {csv_file}")
        df = pd.read_csv(csv_file, encoding='utf-8')
        
        print("CSV columns found:", df.columns.tolist())
        
        # Define the expected Snowflake table columns
        snowflake_columns = [
            'JOB_ID',
            'SEARCH_QUERY',
            'TITLE',
            'COMPANY',
            'LOCATION',
            'DESCRIPTION',
            'POSTED_AT',
            'POSTED_DATE',
            'APPLY_LINKS',
            'JOB_HIGHLIGHTS'
        ]
        
        # Create mapping from CSV columns to Snowflake columns
        csv_to_snowflake_mapping = {
            'job_id': 'JOB_ID',
            'search_query': 'SEARCH_QUERY',
            'title': 'TITLE',
            'company': 'COMPANY',
            'location': 'LOCATION',
            'description': 'DESCRIPTION',
            'posted_at': 'POSTED_AT',
            'posted_date': 'POSTED_DATE',
            'apply_links': 'APPLY_LINKS',
            'job_highlights': 'JOB_HIGHLIGHTS'
        }
        
        # Rename columns to match Snowflake
        print("Mapping CSV columns to Snowflake columns...")
        df = df.rename(columns=csv_to_snowflake_mapping)
        
        # Verify all required columns are present
        missing_columns = set(snowflake_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns in CSV: {missing_columns}")
        
        # Reorder columns to match Snowflake table
        df = df[snowflake_columns]
        
        print(f"Found {len(df)} rows in CSV file")
        
        # Create Snowflake connection
        print("Connecting to Snowflake...")
        conn = snowflake.connector.connect(
            user=snowflake_user,
            password=snowflake_password,
            account=snowflake_account,
            warehouse=snowflake_warehouse,
            role=snowflake_role,
            database=snowflake_database,
            schema=snowflake_schema
        )
        
        try:
            cursor = conn.cursor()
            
            # First, delete all existing data
            print("Deleting existing data from Snowflake table...")
            #delete_query = f"DELETE FROM {snowflake_database}.{snowflake_schema}.TESTJOBSDB"
            delete_query = "DELETE FROM JOBLISTINGS;"
            cursor.execute(delete_query)
            
            # Get count of deleted rows
            deleted_rows = cursor.rowcount
            print(f"Deleted {deleted_rows} existing rows from table")
            
            # Write the new data
            print("Uploading new data to Snowflake...")
            success, nchunks, nrows, output = write_pandas(
                conn=conn,
                df=df,
                #table_name='TESTJOBSDB',
                table_name='JOBLISTINGS',
                database=snowflake_database,
                schema=snowflake_schema,
                quote_identifiers=False
            )
            
            if success:
                print(f"Successfully uploaded {nrows} rows in {nchunks} chunks to Snowflake")
                
                # Verify the upload by counting rows
                #cursor.execute(f"SELECT COUNT(*) FROM {snowflake_database}.{snowflake_schema}.TESTJOBSDB")
                cursor.execute(f"SELECT COUNT(*) FROM {snowflake_database}.{snowflake_schema}.JOBLISTINGS")
                final_count = cursor.fetchone()[0]
                print(f"Final row count in Snowflake table: {final_count}")
                
                if final_count != len(df):
                    print("WARNING: Row count mismatch between CSV and Snowflake table!")
            else:
                print("Upload to Snowflake failed")
                print("Output:", output)
            
        finally:
            cursor.close()
            conn.close()
            print("Snowflake connection closed")
            
    except Exception as e:
        print(f"Error updating Snowflake table: {str(e)}")
        raise

if __name__ == "__main__":
    update_snowflake_from_csv()