from itertools import combinations
import os
import numpy as np
import pandas as pd
import streamlit as st
import networkx as nx
from pybliometrics.scopus import SerialTitle, ScopusSearch, init, create_config

class ConfigManager:
    @staticmethod
    def setup_pybliometrics(config_path, scopus_api_key):
        if scopus_api_key:
            os.environ["SCOPUS_API_KEY"] = scopus_api_key
            create_config(config_dir=config_path, keys=[scopus_api_key])
        else:
            st.warning("No SCOPUS_API_KEY provided. Check your configuration.")
        init(config_path=config_path)

    @staticmethod
    def get_openai_headers(api_key):
        if not api_key:
            st.error("No OPENAI_API_KEY provided!")
            return None
        return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
class SNIPManager:
    snip_cache = {}  # Class-level cache for SNIP values

    @staticmethod
    def get_snip(journal_issn, pub_year):
        key = (journal_issn, pub_year)
        if key in SNIPManager.snip_cache:  # Corrected reference to class-level snip_cache
            return SNIPManager.snip_cache[key]
        if pd.isna(journal_issn) or str(journal_issn).strip() == "" or pd.isna(pub_year):
            SNIPManager.snip_cache[key] = np.nan  # Corrected reference to class-level snip_cache
            return np.nan
        try:
            st_obj = SerialTitle(str(journal_issn), refresh=True, view='ENHANCED')
            if st_obj.sniplist and len(st_obj.sniplist) > 0:
                for yr, snip in st_obj.sniplist:
                    if yr == pub_year:
                        SNIPManager.snip_cache[key] = snip  # Corrected reference to class-level snip_cache
                        return snip
                latest_snip = max(st_obj.sniplist, key=lambda x: x[0])[1]
                SNIPManager.snip_cache[key] = latest_snip  # Corrected reference to class-level snip_cache
                return latest_snip
            else:
                SNIPManager.snip_cache[key] = np.nan  # Corrected reference to class-level snip_cache
                return np.nan
        except Exception as e:
            # st.error(f"Error retrieving SNIP for ISSN {journal_issn}: {e}")
            SNIPManager.snip_cache[key] = np.nan  # Corrected reference to class-level snip_cache
            return np.nan
        
class NetworkBuilder:
    @staticmethod
    def normalize_name(name):
        """
        Normalize names to 'Firstname Lastname' format.
        """
        name = name.strip()
        if ',' in name:  # Format: "Lastname, Firstname"
            last, first = map(str.strip, name.split(',', maxsplit=1))
            return f"{first} {last}"
        return name  # Assume format is already "Firstname Lastname"
    
    @staticmethod
    def build_coauthor_network(df):
        """
        Build a coauthor network from a DataFrame containing author names.

        Args:
            df (pd.DataFrame): DataFrame with an 'author_names' column.

        Returns:
            networkx.Graph: A graph where nodes represent authors and edges represent collaborations.
        """
        # Validate input
        if 'author_names' not in df.columns:
            raise ValueError("The DataFrame must contain an 'author_names' column.")
        
        G = nx.Graph()

        for authors in df['author_names']:
            if authors and isinstance(authors, str):  # Ensure non-empty and valid string
                # Normalize names and split by ';'
                names = [NetworkBuilder.normalize_name(name) for name in authors.split(';') if name.strip()]
                # Generate edges for all pairs of authors
                for pair in combinations(names, 2):
                    if G.has_edge(*pair):
                        G[pair[0]][pair[1]]['weight'] += 1
                    else:
                        G.add_edge(*pair, weight=1)

        return G
    
