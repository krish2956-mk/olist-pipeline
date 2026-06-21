# Data Ingestion Pipeline

An enterprise-ready data engineering pipeline orchestrated by Apache Airflow.

## Architecture Overview
*(Insert Architecture Diagram Here)*

The pipeline ingests data from 3 separate sources, performs validation with Claude 3 Haiku, stores the cleaned data into an idempotent SQLite database, and generates tangible data quality and summary reports.

### Sources
1. **Olist E-Commerce Dataset (CSV)**: Raw customer, order, items, and payments data.
2. **Weather API (JSON)**: Live data fetched from Open-Meteo REST API.
3. **Synthetic Orders (Faker)**: Generated "messy" data to demonstrate data quality checks.

## Setup Instructions

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Copy `.env.example` to `.env` and provide your API keys:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to add your `ANTHROPIC_API_KEY`.

3. **Run the Pipeline**:
   Start the Airflow standalone instance:
   ```bash
   airflow standalone
   ```
   Navigate to `localhost:8080`, enable the `ingestion_dag`, and trigger a run.

## Sample Outputs
*(Insert Screenshot of Data Quality Report Here)*
