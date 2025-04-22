from pathlib import Path
import datetime
from matplotlib import pyplot as plt
import pandas as pd
import streamlit as st
import plotly.express as px
import networkx as nx
from bibliometrics_1.data import DataProcessor
from bibliometrics_1.utils import NetworkBuilder

class Plotter:
    def render_line_graph(self):
        """
        Render a line graph showing monthly publication trends over the last 5 years.
        """
        if hasattr(self, 'df_last_5_years') and not self.df_last_5_years.empty:
            monthly_counts_last_5_years, _ = DataProcessor.aggregate_counts(self.df_last_5_years)
            grouped_counts_last_5_years = monthly_counts_last_5_years.copy()
            grouped_counts_last_5_years['Year'] = grouped_counts_last_5_years['Year'].astype(int)
            grouped_counts_last_5_years['Month'] = grouped_counts_last_5_years['Month'].astype(int)

            # Establish date range
            min_date = datetime.datetime(
                grouped_counts_last_5_years['Year'].min(),
                grouped_counts_last_5_years['Month'].min(),
                1
            )
            max_date = datetime.datetime(
                grouped_counts_last_5_years['Year'].max(),
                grouped_counts_last_5_years['Month'].max(),
                1
            )
            complete_date_range_last_5_years = pd.date_range(start=min_date, end=max_date, freq='MS')

            # Create a DataFrame for the complete date range
            date_range_df_last_5_years = pd.DataFrame({
                'YearMonth': complete_date_range_last_5_years.strftime('%Y-%m'),
                'Year': complete_date_range_last_5_years.year,
                'Month': complete_date_range_last_5_years.month
            })

            # Merge to fill missing months with 0 counts
            grouped_counts_last_5_years = pd.merge(
                date_range_df_last_5_years,
                grouped_counts_last_5_years,
                how='left',
                on=['Year', 'Month']
            )
            grouped_counts_last_5_years['Count'] = grouped_counts_last_5_years['Count'].fillna(0)
            grouped_counts_last_5_years['YearMonth'] = grouped_counts_last_5_years['YearMonth'].astype(str)

            # Filter for the last 5 years
            grouped_counts_last_5_years = grouped_counts_last_5_years[
                grouped_counts_last_5_years['Year'] >= (self.current_year - 4)
            ]

            # Line Graph for the Last 5 Years
            st.subheader("Publication Trends (Last 5 Years)")
            fig = px.line(
                grouped_counts_last_5_years,
                x='YearMonth',
                y='Count',
                markers=True,
                title="Monthly Publication Trend (Last 5 Years)"
            )
            fig.update_yaxes(rangemode="tozero")
            fig.update_traces(line=dict(color="darkgreen"), marker=dict(color="darkgreen"))

            fig.update_xaxes(
                tickmode='array',
                tickvals=grouped_counts_last_5_years['YearMonth'].iloc[::12],  # Label only filtered years
                tickangle=45
            )
            fig.update_layout(
                title=dict(
                    text="Monthly Publication Trend (Last 5 Years",
                    font=dict(color="black", size=18),
                    x=0.3
                ),
                plot_bgcolor="white",
                paper_bgcolor="white",
                font=dict(color="black", size=14),
                xaxis=dict(title_font=dict(color="black"), tickfont=dict(color="black")),
                yaxis=dict(title_font=dict(color="black"), tickfont=dict(color="black"))
            )
            st.plotly_chart(fig, use_container_width=True, key="line_graph_last_5_years")
        else:
            st.warning("No publication data available for rendering trends over the last 5 years.")
            
    def render_violin_plot(self):
        """
        Render a violin plot showing SNIP distribution by year for the last 5 years.
        """
        if hasattr(self, 'df_last_5_years') and not self.df_last_5_years.empty:
            st.header("Violin Plot of SNIP Distribution (Last 5 Years)")

            # Create violin plot
            fig = px.violin(
                self.df_last_5_years,
                x="Year",
                y="SNIP",
                box=True,
                points=False,
                title="SNIP Distribution by Year (Last 5 Years)"
            )
            fig.update_traces(marker_color="darkgreen")
            fig.update_layout(
                title=dict(
                    text="SNIP Distribution by Year (Last 5 Years)",
                    font=dict(color="black", size=18),
                    x=0.3
                ),
                plot_bgcolor="white",
                paper_bgcolor="white",
                font=dict(color="black", size=14),
                xaxis=dict(title_font=dict(color="black"), tickfont=dict(color="black")),
                yaxis=dict(title_font=dict(color="black"), tickfont=dict(color="black")),
                height=600,
                width=800
            )

            # Display plot
            st.plotly_chart(fig, use_container_width=True, key="violin_plot_last_5_years")
        else:
            st.warning("No publication data available for rendering the violin plot.")
            
    def filter_network(self, network, min_collaborations=4):
        """
        Filter the network to include only edges with weight >= min_collaborations.

        Args:
            network (networkx.Graph): The original coauthor network graph.
            min_collaborations (int): Minimum number of collaborations to keep an edge.

        Returns:
            networkx.Graph: A filtered graph with edges meeting the minimum collaboration criteria.
        """
        filtered_network = nx.Graph()
        for u, v, data in network.edges(data=True):
            if data.get("weight", 0) >= min_collaborations:
                filtered_network.add_edge(u, v, weight=data["weight"])
        return filtered_network
            
    def render_coauthor_network(self):
        """
        Render a coauthor network visualization for the last 5 years.
        """
        if hasattr(self, 'df_last_5_years') and 'author_names' in self.df_last_5_years.columns:
            st.write("### Co-Author Network Visualization (Last 5 Years)")

            # Build the co-author network
            coauthor_network = NetworkBuilder.build_coauthor_network(self.df_last_5_years)

            # Filter by minimum collaborations dynamically using a slider
            min_collaborations = st.slider("Minimum Collaborations to Display", 1, 10, 4)
            filtered_coauthor_network = self.filter_network(coauthor_network, min_collaborations=min_collaborations)

            # Visualize the graph
            fig, ax = plt.subplots(figsize=(12, 10))
            pos = nx.spring_layout(filtered_coauthor_network, seed=42, k=1.2, iterations=100)  # Adjusted `k` and iterations

            # Draw nodes with a standard size
            nx.draw_networkx_nodes(
                filtered_coauthor_network, pos, node_size=200, node_color="green", alpha=0.8
            )

            # Draw edges with a standard width
            nx.draw_networkx_edges(
                filtered_coauthor_network, pos, width=1.5, alpha=0.7, edge_color="gray"
            )

            # Add node labels
            nx.draw_networkx_labels(filtered_coauthor_network, pos, font_size=10, font_color="black")

            plt.title("Co-Author Network (Last 5 Years)", fontsize=14)
            plt.axis("off")  # Remove axes
            st.pyplot(fig)
        else:
            st.warning("No author data available for building the coauthor network. Please check the input data.")
