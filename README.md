# 🚀 Next-Gen Data Engineering Pipeline

An enterprise-ready, end-to-end data engineering pipeline featuring **LLM-assisted Data Validation**, **REST API Streaming**, and a **Real-Time Interactive Dashboard**.

## 🌟 Architecture Overview

This project simulates a modern e-commerce data stack (inspired by Olist). It ingests data from multiple disparate sources, cleans it, uses Generative AI as a strict data quality gatekeeper, and exposes the analytics through a beautiful Streamlit dashboard.

### 🛠️ Tech Stack
* **Language:** Python 3
* **Orchestration:** Apache Airflow
* **Data Processing:** Pandas
* **Database:** SQLite (Relational DB)
* **AI Integration:** Google GenAI SDK (Gemini 1.5/2.5 Flash)
* **Frontend Analytics:** Streamlit & Plotly

---

## 🔑 Core Functionalities

### 1. Multi-Source Data Ingestion
* **Historical Batch Data:** Parses, cleans, and deduplicates massive `.csv` dumps from the Olist E-commerce dataset.
* **Live REST API Feeds:** Connects to the `Open-Meteo API` to stream real-time weather data into the database, demonstrating the ability to handle both static batch files and live JSON streams simultaneously.

### 2. GenAI Data Quality Gatekeeper ("The Hard Stop")
Traditional data pipelines use hard-coded rules (`if column == null`) to check data quality. This project utilizes a **Next-Gen AI approach**:
* During ingestion, the pipeline sends a sample of the raw data to the **Gemini Flash LLM**.
* Gemini acts as a semantic data quality inspector, evaluating the rows for logical anomalies (e.g., malformed IDs, impossible geographical state codes, missing `@` symbols in emails).
* **The Hard Stop Architecture:** If Gemini scores the data quality below a `7/10`, the pipeline executes a `ValueError`, immediately halting the Airflow DAG and preventing corrupt data from polluting the downstream database.

### 3. Interactive Analytics Dashboard (Streamlit)
A full-stack BI Dashboard built purely in Python that connects directly to the SQLite database.
* **Overview Metrics:** High-level KPIs (Total Orders, Total Revenue, Top Items).
* **Geospatial & Trend Analysis:** Dynamic Plotly charts showing Revenue by State and Monthly Order Trends.
* **Live Weather Feed:** A dedicated tab that pulls the latest ingested JSON data from the Weather API. Includes an interactive **"🌦️ Fetch Live Weather Now"** button to trigger the Python ingestion script directly from the cloud UI.

### 4. Drag-and-Drop Cloud CSV Uploader
* The dashboard includes an **"📤 Upload Data"** module.
* Users can drag and drop their own raw CSV files into the web browser. 
* The Streamlit app validates the column schemas, cleans the timestamps, runs the Gemini AI Validation live, and if successful, dynamically replaces the database tables and instantly refreshes all charts.

---

## 💻 Setup Instructions (Local Execution)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Create a `.env` file in the root directory and add your Google AI Studio API key:
   ```env
   GEMINI_API_KEY="your_api_key_here"
   ```

3. **Run the Pipeline (Terminal Execution)**:
   ```bash
   # 1. Run the Olist Batch Ingestion
   python -c "import sys, os; sys.path.insert(0, os.path.abspath('.')); from dags.ingestion_dag import run_olist_pipeline; run_olist_pipeline()"
   
   # 2. Run the Analytics Reports (Generates CSVs)
   python analytics/summary_report.py
   ```

4. **Launch the Dashboard**:
   ```bash
   streamlit run dashboard/app.py
   ```

---

## ☁️ Cloud Deployment
This project is fully configured for deployment on **Streamlit Community Cloud**. 
The repository includes a `.gitignore` perfectly configured to protect `.env` secrets and massive `*.csv` / `*.db` files, allowing seamless deployment straight from GitHub.
