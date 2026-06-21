from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
import sqlite3
import sys
import os

# Add the project root to the path so Airflow can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ingestion.extract_clean_olist import extract_and_clean_olist
from ingestion.load_sqlite import load_dataframes_to_sqlite
from ingestion.extract_weather import extract_and_load_weather
from ingestion.generate_synthetic_db import generate_synthetic_data
from analytics.data_quality_report import generate_quality_report

# Setup failure callback
def log_failure_to_db(context):
    """
    Logs task failures to the pipeline_errors SQLite table.
    """
    exception = context.get('exception')
    task_id = context.get('task_instance').task_id
    dag_id = context.get('task_instance').dag_id
    execution_date = context.get('execution_date').isoformat()
    
    conn = sqlite3.connect('/opt/airflow/ecommerce.db') # Path might vary based on Airflow setup
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pipeline_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dag_id TEXT,
            task_id TEXT,
            execution_date TEXT,
            error_message TEXT
        )
    ''')
    cursor.execute('''
        INSERT INTO pipeline_errors (dag_id, task_id, execution_date, error_message)
        VALUES (?, ?, ?, ?)
    ''', (dag_id, task_id, execution_date, str(exception)))
    conn.commit()
    conn.close()

# Wrapper for Olist
def run_olist_pipeline():
    # Assuming Airflow worker runs from the project root or adjust path
    dfs = extract_and_clean_olist(data_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    load_dataframes_to_sqlite(dfs, db_path='ecommerce.db')

default_args = {
    'owner': 'data_engineer',
    'start_date': datetime(2024, 1, 1),
    'on_failure_callback': log_failure_to_db
}

with DAG(
    'ingestion_dag',
    default_args=default_args,
    schedule='@daily',
    catchup=False,
    description='Orchestrates Olist, Weather, and Synthetic Data ingestion'
) as dag:

    # Source 1: Olist Pipeline
    task_olist = PythonOperator(
        task_id='process_olist_data',
        python_callable=run_olist_pipeline
    )

    # Source 2: Weather API
    task_weather = PythonOperator(
        task_id='process_weather_data',
        python_callable=extract_and_load_weather,
        op_kwargs={'db_path': 'ecommerce.db'}
    )

    # Source 3: Synthetic Data
    task_synthetic = PythonOperator(
        task_id='generate_synthetic_data',
        python_callable=generate_synthetic_data,
        op_kwargs={'db_path': 'ecommerce.db'}
    )

    # Final Task: Generate Report
    task_report = PythonOperator(
        task_id='generate_quality_report',
        python_callable=generate_quality_report,
        op_kwargs={'db_path': 'ecommerce.db'}
    )

    # Dependencies: Run sources in parallel, then generate report
    [task_olist, task_weather, task_synthetic] >> task_report
