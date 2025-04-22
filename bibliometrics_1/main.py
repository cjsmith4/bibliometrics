import datetime
from pathlib import Path
import pandas as pd
import streamlit as st
import pygwalker as pyg
from bibliometrics.GUI.data import DataProcessor, MetricsAppBase
from bibliometrics.GUI.plotter import Plotter
from bibliometrics.GUI.predict import QueryConverter
from bibliometrics.GUI.utils import ConfigManager


class AdvancedMetricsApp(MetricsAppBase):
    def __init__(self):
        self.df = pd.DataFrame()
        self.current_year = datetime.datetime.now().year
        self.config_path = Path('./.config/pybliometrics.cfg')
        self.scopus_api_key = st.secrets.get("SCOPUS_API_KEY")
        self.openai_api_key = st.secrets.get("OPENAI_API_KEY")
        self.openai_api_base = st.secrets.get("OPENAI_API_BASE", "https://api.openai.com/v1")
    
        # Setup Pybliometrics configuration
        ConfigManager.setup_pybliometrics(self.config_path, self.scopus_api_key)
        self.api_headers = ConfigManager.get_openai_headers(self.openai_api_key)
    
        self.plotter = Plotter()
        # Initialize session state variables
        st.session_state.setdefault("scopus_query", "")
        st.session_state.setdefault("scopus_df", pd.DataFrame())
        st.session_state.setdefault("pygwalker_html", "")
        st.session_state.setdefault("input_query", "")

    
    @st.cache_data
    def generate_pygwalker_html(df):
        return pyg.walk(df[["title", "Year", "MonthYear", "SNIP", "citedby_count"]], return_html=True)
    
    def display_scopus_data(self):
        st.write("Click below to toggle the pygwalker data viewer. This allows you to create visualizations based on the data provided above.")
        # Option to toggle PyGWalker Viewer
        if st.button("Show PyGWalker Viewer"):
            try:
                # Generate PyGWalker visualization
                walker_html = pyg.walk(
                    self.df[["title", "Year", "MonthYear", "SNIP", "citedby_count"]],
                    return_html=True
                )
                st.components.v1.html(walker_html)
            except Exception as e:
                st.error(f"Error generating PyGWalker visualization: {e}")


    def enrich_and_process_data(self):
        """
        Enrich the DataFrame with SNIP values, reformat columns, and prepare the data.
        """
        if self.df.empty:
            st.info("No data available to process. Please upload a file or execute a query.")
            return  # Early exit if DataFrame is empty

        with st.spinner("Retrieving SNIP values from Elsevier..."):
            self.df = DataProcessor.enrich_with_snip(self.df)

        desired_column_order = ["SNIP", "title", "Year", "Month", "author_names"]
        other_columns = [col for col in self.df.columns if col not in desired_column_order]
        final_column_order = desired_column_order + other_columns
        self.df = self.df[final_column_order]

        # Format MonthYear and Year columns
        self.df["MonthYear"] = self.df["Month"].astype(str) + "-" + self.df["Year"].astype(str)
        self.df["MonthYear"] = self.df["MonthYear"].str.replace(r"\.0", "", regex=True)
        self.df["MonthYear"] = pd.to_datetime(self.df["MonthYear"], format='%m-%Y', errors='coerce')
        self.df["Year"] = pd.to_numeric(self.df["Year"], errors='coerce')
        self.df['Year'] = self.df['Year'].astype('category')

        # Filter data for the last 5 years
        self.df_last_5_years = self.df[self.df['Year'].astype(float) >= (self.current_year - 4)]

    def display_publications_with_snip(self):
        """
        Display the publications enriched with SNIP values in a structured manner.
        """
        if hasattr(self, 'df') and not self.df.empty:
            st.header("Publications with Impact Factor (SNIP)")
    
            # Retrieve SNIP values and enrich the DataFrame
            with st.spinner("Retrieving SNIP values from Elsevier..."):
                self.df = DataProcessor.enrich_with_snip(self.df)
    
            # Reorder columns based on preferences
            desired_column_order = ["SNIP", "title", "Year", "Month", "author_names"]
            other_columns = [col for col in self.df.columns if col not in desired_column_order]
            final_column_order = desired_column_order + other_columns
            self.df = self.df[final_column_order]
    
            # Format MonthYear and Year columns
            self.df["MonthYear"] = self.df["Month"].astype(str) + "-" + self.df["Year"].astype(str)
            self.df["MonthYear"] = self.df["MonthYear"].str.replace(r"\.0", "", regex=True)
            self.df["MonthYear"] = pd.to_datetime(self.df["MonthYear"], format='%m-%Y', errors='coerce')
            self.df["Year"] = pd.to_numeric(self.df["Year"], errors='coerce')
            self.df['Year'] = self.df['Year'].astype('category')
            
            self.df = self.df.sort_values(by="SNIP", ascending=False)
    
            # Display the enriched DataFrame
            st.write(self.df)
        else:
            st.warning("No publications to display. Please load or generate data first.")

    def run(self):
        st.title("Publication Metrics Dashboard")
        st.markdown("""
        This app allows you to explore publication metrics for the Division of Molecular and Translational BioMedicine.
        You can either upload a spreadsheet (e.g., a publication report), a word document with DOI list, **or** enter and execute a Scopus query.
        The app aggregates publications over time, enriches them with SNIP values, and allows for building plots to analyze publication stats.
        """)
    
        self.display_sidebar()
    
        # Reinitialize DataFrame from session state
        if "scopus_df" in st.session_state and not st.session_state["scopus_df"].empty:
            self.df = st.session_state["scopus_df"]
    
        if self.df.empty:
            st.info("Please upload a publication file or execute a Scopus query from the sidebar.")
        else:
            self.enrich_and_process_data()
            self.display_publications_with_snip()
            self.display_scopus_data()
            self.plotter.render_line_graph()
            self.plotter.render_violin_plot()
            self.plotter.render_coauthor_network()


    def display_sidebar(self):
        """
        Display the sidebar for uploading files or entering queries.
        """
        st.sidebar.header("API & Data Input Settings")
        data_source = st.sidebar.radio("Select Data Source", ["Scopus Query", "Upload Spreadsheet"])
        self.df = pd.DataFrame()  # Avoid reinitializing unless necessary
    
        if data_source == "Upload Spreadsheet":
            uploaded_file = st.sidebar.file_uploader("Upload Publications File (CSV, Excel, or DOCX)", type=["csv", "xls", "xlsx", "docx"])
            if uploaded_file:
                if hasattr(self, 'handle_uploaded_file'):
                    self.df = self.handle_uploaded_file(uploaded_file)
                    if self.df.empty:
                        st.warning("No valid data found in the uploaded file.")
                    else:
                        st.session_state["scopus_df"] = self.df  # Persist DataFrame to session state
                        st.success("File uploaded and processed successfully!")
                else:
                    st.error("The 'handle_uploaded_file' method is not defined in this class.")
    
        elif data_source == "Scopus Query":
            st.sidebar.subheader("Enter Search Parameters")
    
            with st.sidebar.expander("LLM Query Conversion", expanded=False):
                conversion_method = st.selectbox(
                    "Select Conversion Method",
                    ["Unformatted to Scopus Query", "PubMed to Scopus Query"]
                )
                st.text_area("Enter your query", height=100, key="input_query")
    
                if st.button("Convert Query", key="llm_query_convert"):
                    prompt_type = "pubmed" if conversion_method == "PubMed to Scopus Query" else "generic"
                    converted_query = QueryConverter.convert_query(
                        st.session_state.input_query, 
                        prompt_type, 
                        self.api_headers, 
                        self.openai_api_base
                    )
    
                    if converted_query:
                        st.session_state.scopus_query = converted_query
                    else:
                        st.error("Conversion failed. Possible reasons: malformed input or API issues.")
    
            st.text_area(
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
                        st.session_state.scopus_df = self.df  # Persist DataFrame to session state

# =============================================================================
# Run the App
# =============================================================================
if __name__ == "__main__":
    app = AdvancedMetricsApp()
    app.run()
