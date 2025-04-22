from pathlib import Path
import re
import streamlit as st
import requests

class QueryConverter:
    @staticmethod
    def preprocess_date_range(input_query):
        """
        Detect and process date ranges within the input query.
        Returns a reformatted string with consistent PUBYEAR conditions.
        """
        date_range_pattern = r"(\d{4})-(\d{4})"
        match = re.search(date_range_pattern, input_query)
        if match:
            start_year = int(match.group(1))
            end_year = int(match.group(2))
            lower_bound = start_year - 1
            upper_bound = end_year + 1
            date_query = f"PUBYEAR > {lower_bound} AND PUBYEAR < {upper_bound}"
            input_query = re.sub(date_range_pattern, date_query, input_query)
        return input_query

    @staticmethod
    def convert_query(query, prompt_type, api_headers, openai_api_base):
        """
        Convert a query using a prompt and OpenAI API.
        Handles multiple query types (PubMed, generic, or CrossRef).

        Args:
            query (str): The input query to be converted.
            prompt_type (str): The type of query (e.g., "pubmed", "generic", "crossref").
            api_headers (dict): API headers for the OpenAI API.
            openai_api_base (str): Base URL for the OpenAI API.

        Returns:
            str: The converted query or None if conversion fails.
        """
        query = QueryConverter.preprocess_date_range(query)

        if prompt_type == "pubmed":
            prompt = (
                f"Convert the following PubMed query into an **equivalent, explicit Scopus query**. "
                f"Ensure that the query strictly matches all conditions and avoids ambiguity. Use the following Scopus field codes:\n"
                f"- `AUTH` for author names (e.g., AUTH(\"LastName, FirstName\"))\n"
                f"- `AFFIL` for affiliations (e.g., AFFIL(\"Department of Physics\"))\n"
                f"- `AF-ID` for affiliation IDs (e.g., numeric IDs like 60004659)\n"
                f"- `TITLE` for document titles (e.g., TITLE(\"Quantum Computing\"))\n"
                f"- `DOI` for Digital Object Identifiers (e.g., DOI(\"10.1234/example.doi\"))\n"
                f"- `KEYWORDS` for keywords (e.g., KEYWORDS(\"Artificial Intelligence\"))\n"
                f"- `PUBYEAR` for publication year (e.g., PUBYEAR = 2024)\n"
                f"- `SOURCE` for journal source (e.g., SOURCE(\"Nature\"))\n\n"
                f"Special Instructions:\n"
                f"- **Always** connect different fields using `AND` to enforce strict matching.\n"
                f"- **Do not include unrelated records** that only partially match the criteria.\n"
                f"- If the query contains **only numeric input**, interpret it as an `AF-ID` (numeric values should not have quotes).\n"
                f"- **Wrap the entire query in parentheses.**\n"
                f"- If an author's name is present, prioritize `AUTH` and `AF-ID` for accuracy.\n"
                f"- Use parentheses to group conditions logically, e.g., (AUTH(\"Smith\") AND AF-ID(12345)).\n"
                f"- For single PUBYEAR ranges, always use `=` (e.g., PUBYEAR = 2024).\n\n"
                f"Query:\n\n{query}\n\n"
                f"Output the result as a **strict and explicitly formatted Scopus query only**."
            )
        elif prompt_type == "generic":
            prompt = (
                f"Convert the following unformatted query into a **strict and valid Scopus query**. "
                f"Ensure that the query explicitly matches all provided conditions. Use the following Scopus field codes:\n"
                f"- `AUTH` for author names (e.g., AUTH(\"LastName, FirstName\"))\n"
                f"- `AFFIL` for affiliations (e.g., AFFIL(\"Department of Physics\"))\n"
                f"- `AF-ID` for affiliation IDs (e.g., numeric IDs like 60004659)\n"
                f"- `TITLE` for document titles (e.g., TITLE(\"Quantum Computing\"))\n"
                f"- `DOI` for Digital Object Identifiers (e.g., DOI(\"10.1234/example.doi\"))\n"
                f"- `KEYWORDS` for keywords (e.g., KEYWORDS(\"Artificial Intelligence\"))\n"
                f"- `PUBYEAR` for publication year (e.g., PUBYEAR = 2024)\n"
                f"- `SOURCE` for journal source (e.g., SOURCE(\"Nature\"))\n\n"
                f"Special Instructions:\n"
                f"- **Always** connect different fields using `AND` to enforce strict matching.\n"
                f"- **Avoid** including unrelated records that only partially match the criteria.\n"
                f"- If the query contains **only numeric input**, interpret it as an `AF-ID` (numeric values should not have quotes).\n"
                f"- **Wrap the entire query in parentheses.**\n"
                f"- Use parentheses to group conditions logically, e.g., (AUTH(\"Smith\") AND AF-ID(12345)).\n"
                f"- For single PUBYEAR ranges, always use `=` (e.g., PUBYEAR = 2024).\n\n"
                f"Query:\n\n{query}\n\n"
                f"Output the result as a **strict and explicitly formatted Scopus query only**."
            )
        elif prompt_type == "crossref":
            prompt = (
                f"Convert the following DOI into a valid CrossRef query format. "
                f"Ensure that the query is correctly formatted for CrossRef API calls. "
                f"Query:\n\n{query}\n\n"
                f"Output the result as a **strict and explicitly formatted CrossRef query only**."
            )
        else:
            raise ValueError(f"Unsupported prompt_type: {prompt_type}")

        # API Request
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 150
        }
        try:
            response = requests.post(f"{openai_api_base}/chat/completions", headers=api_headers, json=payload)
            response.raise_for_status()  # Raise an error for HTTP codes like 4XX/5XX
            response_data = response.json()
            if "choices" in response_data:
                return response_data["choices"][0]["message"]["content"].strip().strip("```")
        except requests.RequestException as e:
            st.error(f"Error during OpenAI API request: {e}")
        return None
