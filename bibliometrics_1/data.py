#A place for data manipulation functionsfrom pathlib import Path
import datetime
from io import BytesIO
import re
from urllib.parse import quote
from docx import Document
import numpy as np
import pandas as pd
import requests
import streamlit as st
from pybliometrics.scopus import SerialTitle, ScopusSearch, init, create_config
from bibliometrics_1.predict import QueryConverter
from bibliometrics_1.utils import SNIPManager

class CrossRefManager:
    @staticmethod
    def is_crossref_available():
        """
        Check if the CrossRef API is functioning.
        """
        try:
            test_url = "https://api.crossref.org/works/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            response = requests.get(test_url, headers=headers)
            return response.status_code == 200
        except Exception:
            return False
    
    @st.cache_data
    def fetch_crossref_data(doi):
        """
        Query CrossRef for publication data using DOI.
        """
        # Correctly referenced static method from CrossRefManager class
        if not CrossRefManager.is_crossref_available():
            st.warning("CrossRef API is not responding. Some data may be missing.")
            return None
        
        try:
            clean_doi = doi.strip().rstrip('.,;!?')
            encoded_doi = quote(clean_doi)
            url = f"https://api.crossref.org/works/{encoded_doi}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    return data["message"]
                else:
                    st.warning("CrossRef response does not contain 'message' key.")
            elif response.status_code == 404:
                pass
            else:
                st.error(f"CrossRef API error {response.status_code}: {response.text}")
        except Exception as e:
            st.error(f"Error querying CrossRef for DOI {clean_doi}: {e}")
        return None
    
    @staticmethod
    @st.cache_data
    def fetch_data_for_dois(dois, api_headers, openai_api_base):
        """
        Query CrossRef and Scopus for publication data using DOIs.

        Args:
            dois (list): List of DOIs to query.
            api_headers (dict): API headers for the OpenAI API.
            openai_api_base (str): Base URL for the OpenAI API.

        Returns:
            pd.DataFrame: A DataFrame containing publication data.
        """
        total_dois = len(dois)
        progress_bar = st.progress(0)
        publication_data = []

        for index, doi in enumerate(dois, start=1):
            clean_doi = doi.strip()
            progress_bar.progress(index / total_dois)
            row_data = {}

            # Convert query using QueryConverter for Scopus data
            converted_query = QueryConverter.convert_query(
                f'DOI("{clean_doi}")',
                prompt_type="generic",
                api_headers=api_headers,
                openai_api_base=openai_api_base
            )
            if converted_query:
                scopus_data = DataProcessor.fetch_scopus_data(converted_query)
                if not scopus_data.empty:
                    row_data = scopus_data.iloc[0].to_dict()

            # Convert query using QueryConverter for CrossRef data
            crossref_query = QueryConverter.convert_query(
                f'DOI("{clean_doi}")',
                prompt_type="crossref",
                api_headers=api_headers,
                openai_api_base=openai_api_base
            )
            if crossref_query:
                crossref_data = CrossRefManager.fetch_crossref_data(clean_doi)
                if crossref_data:
                    row_data.update({
                        "journal_issn": row_data.get("journal_issn") or (
                            crossref_data.get("ISSN", [None])[0] if isinstance(crossref_data.get("ISSN"), list) and crossref_data.get("ISSN") else None
                        ),
                        "publication_date": row_data.get("publication_date") or (
                            crossref_data.get("issued", {}).get("date-parts", [[None]])[0][0] if crossref_data.get("issued") and crossref_data.get("issued").get("date-parts") else None
                        ),
                        "journal_name": row_data.get("journal_name") or (
                            crossref_data.get("container-title", [None])[0] if isinstance(crossref_data.get("container-title"), list) and crossref_data.get("container-title") else None
                        ),
                        "title": row_data.get("title") or (
                            crossref_data.get("title", [None])[0] if isinstance(crossref_data.get("title"), list) and crossref_data.get("title") else None
                        ),
                        "doi": row_data.get("doi") or crossref_data.get("DOI", None),
                        "author_names": row_data.get("author_names") or ", ".join([
                            author.get("given", "") + " " + author.get("family", "")
                            for author in crossref_data.get("author", [])
                        ]) if "author" in crossref_data else None,
                        "citation_count": row_data.get("citation_count") or crossref_data.get("is-referenced-by-count", None),
                        "publication_date": row_data.get("date_published") or crossref_data.get("created", {}).get("date-time", None),
                        "cited_by": crossref_data.get("is-referenced-by-count", None)  # Ensure the cited_by column is populated
                    })

            if row_data:
                publication_data.append(row_data)
            else:
                st.warning(f"No results found for DOI: {clean_doi}")

        progress_bar.empty()

        if publication_data:
            return pd.DataFrame(publication_data)
        else:
            st.warning("No publication data found for the provided DOIs.")
            return pd.DataFrame(columns=["journal_issn", "publication_date", "journal_name", "title", "doi", "author_names", "citation_count", "date_published"])
    
        progress_bar.empty()
    
        if publication_data:
            return pd.DataFrame(publication_data)
        else:
            st.warning("No publication data found for the provided DOIs.")
            return pd.DataFrame(columns=["journal_issn", "publication_date", "journal_name", "title", "doi", "author_names", "citation_count", "date_published"])
        
class DataProcessor:
    @staticmethod
    def fetch_scopus_data(query):
        """
        Execute a Scopus query and return the results as a DataFrame.

        Args:
            query (str): The Scopus query string.

        Returns:
            pd.DataFrame: DataFrame containing Scopus search results.
        """
        try:
            # Perform Scopus search using ScopusSearch from pybliometrics
            search = ScopusSearch(query)
            if not search.results:
                return pd.DataFrame()  # Return an empty DataFrame if no results are found
            
            # Convert results to a DataFrame
            df = pd.DataFrame(search.results)
            
            # Process and add relevant columns
            if 'coverDate' in df.columns:
                df['publication_date'] = pd.to_datetime(df['coverDate'], errors='coerce')
            if 'publicationName' in df.columns:
                df['journal_name'] = df['publicationName']
            if 'issn' in df.columns:
                df['journal_issn'] = df['issn']

            return df
        except Exception as e:
            # Provide feedback for debugging or errors
            st.error(f"Error executing Scopus query: {query}. {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame on error
        
    @staticmethod
    @st.cache_data
    def load_data(file):
        if file.name.endswith('.csv'):
            return pd.read_csv(file)
        elif file.name.endswith(('.xls', '.xlsx')):
            return pd.read_excel(file)
        elif file.name.endswith('.docx'):
            return DataProcessor.extract_dois_from_docx(file)
        return pd.DataFrame()

    @staticmethod
    @st.cache_data
    def process_data(df):
        # Ensure 'publication_date' is in datetime format
        df['publication_date'] = pd.to_datetime(df['publication_date'], errors='coerce')
    
        # Extract 'Year' and 'Month' columns
        df['Year'] = df['publication_date'].dt.year
        df['Month'] = df['publication_date'].dt.month
    
        # Combine 'Year' and 'Month' to create 'MonthYear'
        df['MonthYear'] = df['Month'].astype(str) + "-" + df['Year'].astype(str)
    
        return df

    @staticmethod
    def extract_dois_from_docx(file):
        document = Document(BytesIO(file.read()))
        text = " ".join(para.text.strip() for para in document.paragraphs)
        return list(set(re.findall(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text)))
        
    
    def fetch_scopus_data(query):
        try:
            search = ScopusSearch(query)
            if not search.results:
                return pd.DataFrame()
            df = pd.DataFrame(search.results)
            if 'coverDate' in df.columns:
                df['publication_date'] = pd.to_datetime(df['coverDate'], errors='coerce')
            if 'publicationName' in df.columns:
                df['journal_name'] = df['publicationName']
            if 'issn' in df.columns:
                df['journal_issn'] = df['issn']
            return df
        except Exception as e:
            st.error(f"Error executing Scopus query: {query}. {str(e)}")
            return pd.DataFrame()
    
    @st.cache_data
    def aggregate_counts(df):
        monthly_counts = df.groupby(['Year', 'Month']).size().reset_index(name='Count')
        yearly_counts = df.groupby('Year').size().reset_index(name='Count')
        return monthly_counts, yearly_counts
    
    @staticmethod
    @st.cache_data
    def enrich_with_snip(df):
        """
        Enrich the DataFrame with SNIP values using journal ISSN and publication year.
        """
        unique_pairs = df[['journal_issn', 'Year']].drop_duplicates()
        snip_mapping = {}
    
        for _, row in unique_pairs.iterrows():
            issn = row['journal_issn']
            year = row['Year']
            # Use the fully qualified name to call `get_snip`
            snip_mapping[(issn, year)] = SNIPManager.get_snip(issn, year)
    
        # Apply SNIP values to the DataFrame
        df['SNIP'] = df.apply(lambda row: snip_mapping.get((row['journal_issn'], row['Year']), np.nan), axis=1)
        return df
    
class MetricsAppBase:
    def handle_uploaded_file(self, file):
        if not hasattr(file, 'name') or not isinstance(file.name, str):
            st.error("Invalid file uploaded. Please try again.")
            return pd.DataFrame()
    
        filename = file.name.lower()
        try:
            if filename.endswith(('.csv', '.xls', '.xlsx')):
                df = DataProcessor.load_data(file)
                processed_df = DataProcessor.process_data(df)
                st.session_state["scopus_df"] = processed_df  # Persist processed DataFrame
                return processed_df
            elif filename.endswith('.docx'):
                dois = DataProcessor.extract_dois_from_docx(file)
                if dois:
                    raw_df = CrossRefManager.fetch_data_for_dois(dois, self.api_headers, self.openai_api_base)
                    processed_df = DataProcessor.process_data(raw_df)
                    st.session_state["scopus_df"] = processed_df  # Persist processed DataFrame
                    return processed_df
                else:
                    st.error("No DOIs found in the uploaded DOCX file!")
            else:
                st.error("Unsupported file type. Please upload a valid CSV, Excel, or DOCX file.")
        except Exception as e:
            st.error(f"Error processing file: {e}")
        return pd.DataFrame()
        
class BasicMetricsApp(MetricsAppBase):
    def __init__(self):
        self.df = pd.DataFrame()
        self.current_year = datetime.datetime.now().year

    def run(self):
        """
        Main entry point for the Streamlit app.
        """
        st.title("Publication Metrics Dashboard")
        st.markdown("""
        This app allows you to explore publication metrics for the Division of Molecular and Translational BioMedicine.
        You can either upload a spreadsheet (e.g., a publication report), a word document with DOI list, **or** enter and execute a Scopus query.
        The app aggregates publications over time, enriches them with SNIP 
        (Source-Normalized Impact per Paper) values, and allows for building plots to analyze publication stats.
        """)

        # Sidebar: API & Data Input Settings
        st.sidebar.header("API & Data Input Settings")
        data_source = st.sidebar.radio("Select Data Source", ["Scopus Query", "Upload Spreadsheet"])
        df = pd.DataFrame()

        if data_source == "Upload Spreadsheet":
            uploaded_file = st.sidebar.file_uploader("Upload Publications File (CSV, Excel, or DOCX)", type=["csv", "xls", "xlsx", "docx"])
            if uploaded_file:
                df = self.handle_uploaded_file(uploaded_file)

        elif data_source == "Scopus Query":
            st.sidebar.subheader("Enter Search Parameters")

            # Sidebar widget logic
            with st.sidebar.expander("LLM Query Conversion", expanded=False):
                conversion_method = st.selectbox(
                    "Select Conversion Method",
                    ["Unformatted to Scopus Query", "PubMed to Scopus Query"]
                )
                input_query = st.text_area("Enter your query", height=100, key="input_query")
            
                if st.button("Convert Query", key="llm_query_convert"):
                    prompt_type = "pubmed" if conversion_method == "PubMed to Scopus Query" else "generic"
                    converted_query = QueryConverter.convert_query(st.session_state.input_query, prompt_type, self.api_headers, self.openai_api_base)
            
                    if converted_query:
                        st.session_state.scopus_query = converted_query
                    else:
                        st.error("Conversion failed. Possible reasons: malformed input or API issues.")
            
            # Direct Scopus query input and execution
            scopus_query = st.sidebar.text_area(
                "Enter Scopus Query Directly",
                value=st.session_state.get("scopus_query", ""),
                height=100,
                key="direct_query"
            )
            
            if st.sidebar.button("Execute Query", key="execute_scopus"):
                with st.spinner("Executing Scopus query..."):
                    self.df = DataProcessor.fetch_scopus_data(st.session_state.scopus_query)
                    if self.df.empty:
                        st.warning("No data found for the Scopus query. Please refine your query.")
                    else:
                        self.df = DataProcessor.process_data(self.df)
                        st.session_state["scopus_df"] = self.df  # Persist DataFrame to session state
