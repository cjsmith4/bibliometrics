# Publication Metrics Dashboard

## Overview

This application is a **Streamlit-based dashboard** designed to analyze publication metrics for the **Division of Molecular and Translational BioMedicine** or similar entities. Users can upload publication files or execute Scopus queries to extract, enrich, and visualize publication data, including metrics such as **SNIP (Source-Normalized Impact per Paper)** and co-author networks.

## Features

- **API Integration**:
  - Pybliometrics for Scopus queries.
  - CrossRef for DOI-related data enrichment.
  - OpenAI for query conversion.
- **Data Input**:
  - Accepts `.csv`, `.xls`, `.xlsx`, and `.docx` files.
  - Allows direct Scopus query input and execution.
- **Visualization**:
  - Monthly publication trends (line graph).
  - SNIP distribution (violin plot).
  - Co-author collaboration networks.
  - PyGWalker integration for interactive data exploration.
- **Data Processing**:
  - Aggregation of publication metrics over time.
  - Enrichment with SNIP values.
  - Extraction of DOIs from `.docx` files.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Setup API keys:
   - Add the **Scopus API Key** and **OpenAI API Key** to your environment variables or secrets configuration.

4. Run the application:
   ```bash
   streamlit run app.py
   ```

## Code Structure

### 1. Configuration Manager (`ConfigManager`)
Handles setup for Pybliometrics and OpenAI API integration. Ensures proper authentication.

### 2. Query Conversion (`QueryConverter`)
Converts user-provided queries (e.g., PubMed queries) into strict Scopus or CrossRef query formats using OpenAI's GPT models.

### 3. Data Processing (`DataProcessor`)
Provides functions to:
- Load and preprocess data files.
- Enrich publication data with SNIP values.
- Aggregate publication counts.
- Extract DOIs from `.docx` files.

### 4. Network Builder (`NetworkBuilder`)
Creates co-author networks based on collaboration patterns extracted from publication data.

### 5. Metrics App Classes (`MetricsAppBase`, `BasicMetricsApp`, `AdvancedMetricsApp`)
These define the Streamlit application logic for user interaction, file processing, data visualization, and dashboard functionalities.

## Key Libraries Used

- **Streamlit**: To create the dashboard interface.
- **Pybliometrics**: For Scopus data queries.
- **NetworkX**: To construct and visualize co-author networks.
- **Plotly**: For interactive graph visualizations.
- **PyGWalker**: For data exploration.
- **Pandas & NumPy**: For efficient data handling.

## Usage Instructions

### Upload Spreadsheet
1. Navigate to the **Upload Spreadsheet** section.
2. Upload a `.csv`, `.xlsx`, or `.docx` file containing publication data.
3. View and explore aggregated metrics.

### Query Scopus
1. Enter a Scopus query directly in the sidebar.
2. Execute the query and review publication data fetched from Scopus.

### Visualization
1. Use PyGWalker for detailed visual analysis.
2. Analyze SNIP values, monthly publication trends, and co-author networks directly on the dashboard.

## Contributing

Contributions to enhance the functionality or add new features are welcome. Please open an issue or submit a pull request.

## License

