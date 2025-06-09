import streamlit as st
import pandas as pd
import io
import plotly.express as px
import plotly.io as pio
from pyvis.network import Network
import streamlit.components.v1 as components

# --- SET UP STREAMLIT PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Carrier Relationship Viewer",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔍 Carrier Relationship Viewer")
st.markdown("---")
st.write("Upload your Excel/CSV file to explore broker relationships for each carrier.")

# --- FILE UPLOADER ---
st.sidebar.header("📂 Upload Data File")
uploaded_file = st.sidebar.file_uploader(
    "Choose your Carrier Relationships file",
    type=["xlsx", "csv"]
)

# --- ABOUT / HELP SECTION ---
with st.sidebar.expander("ℹ️ About this App"):
    st.write(
        """
        This app allows you to explore the relationships between Carriers and Brokers.
        Upload your data file containing 'Carrier', 'Brokers to', 'Brokers through',
        'broker entity of', and 'relationship owner' columns.
        """
    )
    st.write(
        """
        **How to use:**
        1. Upload your `.xlsx` or `.csv` file in the sidebar.
        2. Use the search bar or dropdown to find a specific Carrier(s).
        3. Apply global filters in the sidebar to narrow down your data.
        4. View summarized statistics and detailed relationship information.
        5. Download the displayed details for selected carriers.
        """
    )
    st.write("---")
    st.write("Developed with Streamlit.")

# --- IN-APP SAMPLE FILE DOWNLOAD (Only in sidebar) ---
st.sidebar.header("📝 Sample File")
sample_data = {
    'Carrier': ['Carrier A', 'Carrier B', 'Carrier C', 'Carrier D', 'Carrier E'],
    'Brokers to': ['Broker Alpha, Broker Beta', 'Broker Gamma', 'Broker Delta', '', 'Broker Zeta'],
    'Brokers through': ['Broker 123', 'Broker 456, Broker 789', 'Broker 010', 'Broker 111', ''],
    'broker entity of': ['Entity X', 'Entity Y', 'Entity Z', 'Entity X', 'Entity Y'],
    'relationship owner': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown', 'John Doe']
}
sample_df = pd.DataFrame(sample_data)
csv_sample = sample_df.to_csv(index=False).encode('utf-8')

st.sidebar.download_button(
    label="⬇️ Download Sample Data File",
    data=csv_sample,
    file_name='Sample Carrier Relationships.csv',
    mime='text/csv',
    help="Download a sample CSV file with the correct column headers.",
    key="sample_download_sidebar"
)

# --- Caching Data Loading and Processing ---
@st.cache_data
def load_and_process_data(file_buffer, file_type):
    """Loads and processes the uploaded Excel/CSV file."""
    df = None
    if file_type == 'csv':
        df = pd.read_csv(file_buffer)
    elif file_type == 'xlsx':
        df = pd.read_excel(file_buffer)

    df.columns = df.columns.str.strip() # Clean column names

    expected_columns = [
        "Carrier",
        "Brokers to",
        "Brokers through",
        "broker entity of",
        "relationship owner"
    ]

    # Check if all expected columns are present
    if not all(col in df.columns for col in expected_columns):
        missing_cols = [col for col in expected_columns if col not in df.columns]
        st.error(f"Missing required columns in the uploaded file: **{', '.join(missing_cols)}**")
        st.write("Please ensure your file has the following exact column headers:")
        st.code(", ".join(expected_columns))
        st.stop()

    # --- Data Aggregation for carrier_data dictionary ---
    carrier_data = {}
    all_brokers_to = set()
    all_brokers_through = set()
    all_broker_entities = set()
    all_relationship_owners = set()

    for index, row in df.iterrows():
        carrier = str(row['Carrier']).strip() if pd.notna(row['Carrier']) else "Unnamed Carrier"
        
        if not carrier:
            carrier = "Unnamed Carrier"

        if carrier == "Unnamed Carrier" and all(pd.isna(row[col]) or not str(row[col]).strip() for col in expected_columns[1:]):
            continue

        if carrier not in carrier_data:
            carrier_data[carrier] = {
                'Brokers to': set(),
                'Brokers through': set(),
                'broker entity of': set(),
                'relationship owner': set(),
                'original_rows': []
            }
        
        carrier_data[carrier]['original_rows'].append(index)

        # Process 'Brokers to'
        brokers_to_val = str(row['Brokers to']).strip() if pd.notna(row['Brokers to']) else ""
        if brokers_to_val:
            for broker in [b.strip() for b in brokers_to_val.split(',') if b.strip()]:
                carrier_data[carrier]['Brokers to'].add(broker)
                all_brokers_to.add(broker)

        # Process 'Brokers through'
        brokers_through_val = str(row['Brokers through']).strip() if pd.notna(row['Brokers through']) else ""
        if brokers_through_val:
            for broker in [b.strip() for b in brokers_through_val.split(',') if b.strip()]:
                carrier_data[carrier]['Brokers through'].add(broker)
                all_brokers_through.add(broker)

        # Process 'broker entity of'
        broker_entity_val = str(row['broker entity of']).strip() if pd.notna(row['broker entity of']) else ""
        if broker_entity_val:
            carrier_data[carrier]['broker entity of'].add(broker_entity_val)
            all_broker_entities.add(broker_entity_val)

        # Process 'relationship owner'
        relationship_owner_val = str(row['relationship owner']).strip() if pd.notna(row['relationship owner']) else ""
        if relationship_owner_val:
            carrier_data[carrier]['relationship owner'].add(relationship_owner_val)
            all_relationship_owners.add(relationship_owner_val)

    # Convert sets to sorted lists for consistent display
    for carrier, data_dict in carrier_data.items():
        for key in ['Brokers to', 'Brokers through', 'broker entity of', 'relationship owner']:
            carrier_data[carrier][key] = sorted(list(data_dict[key]))

    return df, carrier_data, all_brokers_to, all_brokers_through, all_broker_entities, all_relationship_owners

# --- Main App Logic ---
if uploaded_file is not None:
    file_type = uploaded_file.name.split('.')[-1]
    df, carrier_data, all_brokers_to, all_brokers_through, all_broker_entities, all_relationship_owners = load_and_process_data(uploaded_file, file_type)

    unique_carriers = sorted(list(carrier_data.keys()))

    # --- GLOBAL FILTERS ---
    st.sidebar.header("⚙️ Global Filters")

    # Initialize session state for filters if not already present
    if "filter_brokers_to_val" not in st.session_state:
        st.session_state.filter_brokers_to_val = []
    if "filter_brokers_through_val" not in st.session_state:
        st.session_state.filter_brokers_through_val = []
    if "filter_broker_entity_val" not in st.session_state:
        st.session_state.filter_broker_entity_val = []
    if "filter_relationship_owner_val" not in st.session_state:
        st.session_state.filter_relationship_owner_val = []
    if "carrier_search_input_val" not in st.session_state:
        st.session_state.carrier_search_input_val = ""
    if "carrier_multiselect_val" not in st.session_state:
        st.session_state.carrier_multiselect_val = []

    # Clear All Filters Button
    def clear_filters():
        st.session_state.filter_brokers_to_val = []
        st.session_state.filter_brokers_through_val = []
        st.session_state.filter_broker_entity_val = []
        st.session_state.filter_relationship_owner_val = []
        st.session_state.carrier_search_input_val = ""
        st.session_state.carrier_multiselect_val = []
        st.rerun()

    st.sidebar.button("🗑️ Clear All Filters", on_click=clear_filters)

    selected_filter_brokers_to = st.sidebar.multiselect(
        "Filter by 'Brokers to'",
        options=sorted(list(all_brokers_to)),
        key="filter_brokers_to_val",
        default=st.session_state.filter_brokers_to_val
    )
    selected_filter_brokers_through = st.sidebar.multiselect(
        "Filter by 'Brokers through'",
        options=sorted(list(all_brokers_through)),
        key="filter_brokers_through_val",
        default=st.session_state.filter_brokers_through_val
    )
    selected_filter_broker_entity = st.sidebar.multiselect(
        "Filter by 'broker entity of'",
        options=sorted(list(all_broker_entities)),
        key="filter_broker_entity_val",
        default=st.session_state.filter_broker_entity_val
    )
    selected_filter_relationship_owner = st.sidebar.multiselect(
        "Filter by 'relationship owner'",
        options=sorted(list(all_relationship_owners)),
        key="filter_relationship_owner_val",
        default=st.session_state.filter_relationship_owner_val
    )

    # Apply global filters to narrow down the list of carriers for selection AND visualization
    filtered_unique_carriers_for_selection = []
    filtered_carrier_data_for_viz = {}

    for carrier in unique_carriers:
        include_carrier = True
        info = carrier_data[carrier]

        if selected_filter_brokers_to:
            if not any(b in selected_filter_brokers_to for b in info['Brokers to']):
                include_carrier = False
        if selected_filter_brokers_through:
            if not any(b in selected_filter_brokers_through for b in info['Brokers through']):
                include_carrier = False
        if selected_filter_broker_entity:
            if not any(e in selected_filter_broker_entity for e in info['broker entity of']):
                include_carrier = False
        if selected_filter_relationship_owner:
            if not any(r in selected_filter_relationship_owner for r in info['relationship owner']):
                include_carrier = False
        
        if include_carrier:
            filtered_unique_carriers_for_selection.append(carrier)
            filtered_carrier_data_for_viz[carrier] = info
    
    filtered_unique_carriers_for_selection = sorted(filtered_unique_carriers_for_selection)

    # --- SUMMARY STATISTICS ---
    st.markdown("## 📈 Data Overview")
    col_count1, col_count2, col_count3, col_count4, col_count5 = st.columns(5)

    with col_count1:
        st.metric(label="Total Unique Carriers (Original)", value=len(unique_carriers))
    with col_count2:
        st.metric(label="Unique 'Brokers to' (Original)", value=len(all_brokers_to))
    with col_count3:
        st.metric(label="Unique 'Brokers through' (Original)", value=len(all_brokers_through))
    with col_count4:
        st.metric(label="Unique Broker Entities (Original)", value=len(all_broker_entities))
    with col_count5:
        st.metric(label="Unique Relationship Owners (Original)", value=len(all_relationship_owners))
    st.markdown("---")


    # --- CARRIER SEARCH AND SELECTION ---
    st.header("Select Carrier(s) for Details")
    
    # Search bar
    search_query = st.text_input(
        "Type to search for a Carrier:",
        value=st.session_state.carrier_search_input_val,
        key="carrier_search_input_val"
    ).strip()

    # Filter carriers based on search query AND global filters (using filtered_unique_carriers_for_selection)
    search_filtered_carriers = [
        carrier for carrier in filtered_unique_carriers_for_selection
        if search_query.lower() in carrier.lower()
    ]
    
    # --- Feedback on filter results ---
    if search_query or any([selected_filter_brokers_to, selected_filter_brokers_through, selected_filter_broker_entity, selected_filter_relationship_owner]):
        st.info(f"Found **{len(search_filtered_carriers)}** carriers matching your search and filters.")
        if not search_filtered_carriers:
            st.warning("Adjust filters or search query to find more carriers.")


    if not search_filtered_carriers and search_query:
        selected_carriers = []
    else:
        selected_carriers = st.multiselect(
            "✨ Choose one or more Carriers from the filtered list:",
            options=search_filtered_carriers,
            default=st.session_state.carrier_multiselect_val if search_query == st.session_state.carrier_search_input_val else [],
            key="carrier_multiselect_val"
        )
    st.markdown("---")

    # --- DISPLAY RESULTS ---
    if selected_carriers:
        st.subheader(f"📊 Details for Selected Carriers:")
        
        # Consolidate details for multi-select
        combined_details = {
            'Brokers to': set(),
            'Brokers through': set(),
            'broker entity of': set(),
            'relationship owner': set(),
            'carrier_specific_details': {}
        }
        
        download_rows = []

        for carrier in selected_carriers:
            if carrier in carrier_data:
                info = carrier_data[carrier]
                
                combined_details['Brokers to'].update(info['Brokers to'])
                combined_details['Brokers through'].update(info['Brokers through'])
                combined_details['broker entity of'].update(info['broker entity of'])
                combined_details['relationship owner'].update(info['relationship owner'])

                download_rows.append({
                    "Carrier": carrier,
                    "Brokers to": ", ".join(info['Brokers to']),
                    "Brokers through": ", ".join(info['Brokers through']),
                    "broker entity of": ", ".join(info['broker entity of']),
                    "relationship owner": ", ".join(info['relationship owner'])
                })
            else:
                st.warning(f"Data for '**{carrier}**' not found after processing. Please check your file data.")

        # --- Display Combined Details ---
        if len(selected_carriers) > 1:
            st.markdown("### Combined Unique Relationships:")
            col_combined1, col_combined2 = st.columns(2)
            col_combined3, col_combined4 = st.columns(2)

            with col_combined1:
                st.markdown("#### 👉 Brokers To:")
                if combined_details['Brokers to']:
                    for broker in sorted(list(combined_details['Brokers to'])):
                        st.markdown(f"- **{broker}**")
                else:
                    st.info("No 'Brokers to' found for selected carriers.")
            
            with col_combined2:
                st.markdown("#### 🤝 Brokers Through:")
                if combined_details['Brokers through']:
                    for broker in sorted(list(combined_details['Brokers through'])):
                        st.markdown(f"- **{broker}**")
                else:
                    st.info("No 'Brokers through' found for selected carriers.")
            
            with col_combined3:
                st.markdown("#### 🏢 Broker Entity Of:")
                if combined_details['broker entity of']:
                    for entity in sorted(list(combined_details['broker entity of'])):
                        st.markdown(f"- **{entity}**")
                else:
                    st.info("No 'broker entity of' found for selected carriers.")
            
            with col_combined4:
                st.markdown("#### 👤 Relationship Owner:")
                if combined_details['relationship owner']:
                    for owner in sorted(list(combined_details['relationship owner'])):
                        st.markdown(f"- **{owner}**")
                else:
                    st.info("No 'relationship owner' found for selected carriers.")
            st.markdown("---")

        # --- Display Individual Carrier Details ---
        if selected_carriers:
            st.markdown("### Individual Carrier Details:")
            for carrier_idx, carrier in enumerate(selected_carriers):
                if carrier in carrier_data:
                    st.markdown(f"##### Details for **{carrier}**:")
                    info = carrier_data[carrier]

                    col_ind1, col_ind2 = st.columns(2)
                    col_ind3, col_ind4 = st.columns(2)

                    with col_ind1:
                        st.markdown("**👉 Brokers To:**")
                        if info['Brokers to']:
                            for broker in info['Brokers to']:
                                st.markdown(f"- {broker}")
                        else:
                            st.markdown("*(None)*")

                    with col_ind2:
                        st.markdown("**🤝 Brokers Through:**")
                        if info['Brokers through']:
                            for broker in info['Brokers through']:
                                st.markdown(f"- {broker}")
                        else:
                            st.markdown("*(None)*")
                    
                    with col_ind3:
                        st.markdown("**🏢 Broker Entity Of:**")
                        if info['broker entity of']:
                            for entity in info['broker entity of']:
                                st.markdown(f"- {entity}")
                        else:
                            st.markdown("*(None)*")

                    with col_ind4:
                        st.markdown("**👤 Relationship Owner:**")
                        if info['relationship owner']:
                            for owner in info['relationship owner']:
                                st.markdown(f"- {owner}")
                        else:
                            st.markdown("*(None)*")
                    
                    if carrier_idx < len(selected_carriers) - 1:
                        st.markdown("---")
            st.markdown("---")


        # --- DOWNLOAD BUTTON ---
        if download_rows:
            download_df = pd.DataFrame(download_rows)
            csv_string = download_df.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label=f"⬇️ Download Details for Selected Carriers ({len(selected_carriers)})",
                data=csv_string,
                file_name=f"selected_carriers_relationships.csv",
                mime="text/csv",
                help="Download the displayed information for the selected carriers as a CSV file.",
                key="selected_carriers_download"
            )

    else:
        st.info("⬆️ Please select one or more carriers from the dropdown above to view their details.")

    # --- VISUALIZATIONS (NOW FILTERED) ---
    st.markdown("---")
    st.markdown("## 📊 Relationship Visualizations (Filtered Data)")

    # Bar chart for Top Brokers To
    brokers_to_counts = pd.Series([b for carrier_info in filtered_carrier_data_for_viz.values() for b in carrier_info['Brokers to']])
    if not brokers_to_counts.empty:
        top_brokers_to = brokers_to_counts.value_counts().reset_index()
        top_brokers_to.columns = ['Broker', 'Count']
        fig_brokers_to = px.bar(
            top_brokers_to.head(10),
            x='Broker',
            y='Count',
            title='Top 10 "Brokers To" by Carrier Associations (Filtered)',
            labels={'Broker': 'Broker (To)', 'Count': 'Number of Carriers'},
            height=400
        )
        st.plotly_chart(fig_brokers_to, use_container_width=True)
        img_bytes_brokers_to = pio.to_image(fig_brokers_to, format='png')
        st.download_button(
            label="🖼️ Download 'Brokers To' Chart",
            data=img_bytes_brokers_to,
            file_name="brokers_to_chart.png",
            mime="image/png",
            key="download_brokers_to_chart"
        )
    else:
        st.info("No 'Brokers to' data available for visualization with current filters.")

    # Bar chart for Top Brokers Through
    brokers_through_counts = pd.Series([b for carrier_info in filtered_carrier_data_for_viz.values() for b in carrier_info['Brokers through']])
    if not brokers_through_counts.empty:
        top_brokers_through = brokers_through_counts.value_counts().reset_index()
        top_brokers_through.columns = ['Broker', 'Count']
        fig_brokers_through = px.bar(
            top_brokers_through.head(10),
            x='Broker',
            y='Count',
            title='Top 10 "Brokers Through" by Carrier Associations (Filtered)',
            labels={'Broker': 'Broker (Through)', 'Count': 'Number of Carriers'},
            height=400
        )
        st.plotly_chart(fig_brokers_through, use_container_width=True)
        img_bytes_brokers_through = pio.to_image(fig_brokers_through, format='png')
        st.download_button(
            label="🖼️ Download 'Brokers Through' Chart",
            data=img_bytes_brokers_through,
            file_name="brokers_through_chart.png",
            mime="image/png",
            key="download_brokers_through_chart"
        )
    else:
        st.info("No 'Brokers through' data available for visualization with current filters.")

    # Bar chart for Relationship Owners Distribution
    relationship_owners_counts = pd.Series([o for carrier_info in filtered_carrier_data_for_viz.values() for o in carrier_info['relationship owner']])
    if not relationship_owners_counts.empty:
        owner_distribution = relationship_owners_counts.value_counts().reset_index()
        owner_distribution.columns = ['Owner', 'Count']
        fig_owners = px.bar(
            owner_distribution,
            x='Owner',
            y='Count',
            title='Distribution of Relationship Owners (Filtered)',
            labels={'Owner': 'Relationship Owner', 'Count': 'Number of Carriers'},
            height=400
        )
        st.plotly_chart(fig_owners, use_container_width=True)
        img_bytes_owners = pio.to_image(fig_owners, format='png')
        st.download_button(
            label="🖼️ Download 'Relationship Owners' Chart",
            data=img_bytes_owners,
            file_name="relationship_owners_chart.png",
            mime="image/png",
            key="download_owners_chart"
        )
    else:
        st.info("No 'Relationship Owner' data available for visualization with current filters.")

    st.markdown("---")
    st.markdown("## 🕸️ Interactive Network Visualization")

    # --- Legend for Network Graph ---
    st.markdown("### Network Legend:")
    st.markdown(
        """
        <style>
        .legend-item {
            display: flex;
            align-items: center;
            margin-bottom: 5px;
        }
        .legend-color-box {
            width: 20px;
            height: 20px;
            border-radius: 50%; /* For circles */
            margin-right: 8px;
            border: 1px solid #333; /* A slight border for contrast */
        }
        .legend-shape-square {
            width: 20px;
            height: 20px;
            margin-right: 8px;
            border: 1px solid #333;
        }
        .legend-shape-triangle {
            width: 0;
            height: 0;
            border-left: 10px solid transparent;
            border-right: 10px solid transparent;
            border-bottom: 20px solid var(--color); /* Triangle pointing up */
            margin-right: 8px;
        }
        .legend-shape-diamond {
            width: 20px;
            height: 20px;
            margin-right: 8px;
            transform: rotate(45deg);
            border: 1px solid #333;
        }
        .legend-shape-star {
            width: 20px;
            height: 20px;
            margin-right: 8px;
            clip-path: polygon(
                50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%,
                50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%
            );
            border: 1px solid #333;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Updated node colors and shapes for better distinction
    node_colors = {
        'carrier': '#ADD8E6', # Light Blue
        'broker_to': '#66CDAA',  # Medium Aquamarine
        'broker_through': '#FF8C00', # Dark Orange
        'entity': '#FFD700',  # Gold
        'owner': '#FFB6C1'    # Light Pink
    }
    node_shapes = {
        'carrier': 'dot',
        'broker_to': 'square',
        'broker_through': 'triangle',
        'entity': 'diamond',
        'owner': 'star'
    }


    col_legend1, col_legend2, col_legend3, col_legend4, col_legend5 = st.columns(5)
    with col_legend1:
        st.markdown(
            f"<div class='legend-item'><div class='legend-color-box' style='background-color:{node_colors['carrier']}'></div> Carrier</div>",
            unsafe_allow_html=True
        )
    with col_legend2:
        st.markdown(
            f"<div class='legend-item'><div class='legend-shape-square' style='background-color:{node_colors['broker_to']}'></div> Broker (To)</div>",
            unsafe_allow_html=True
        )
    with col_legend3:
        st.markdown(
            f"<div class='legend-item'><div class='legend-shape-triangle' style='--color:{node_colors['broker_through']}'></div> Broker (Through)</div>",
            unsafe_allow_html=True
        )
    with col_legend4:
        st.markdown(
            f"<div class='legend-item'><div class='legend-shape-diamond' style='background-color:{node_colors['entity']}'></div> Broker Entity</div>",
            unsafe_allow_html=True
        )
    with col_legend5:
        st.markdown(
            f"<div class='legend-item'><div class='legend-shape-star' style='background-color:{node_colors['owner']}'></div> Relationship Owner</div>",
            unsafe_allow_html=True
        )
    st.markdown("---")

    # --- Determine data source for network graph based on selected_carriers ---
    if selected_carriers:
        network_source_data = {
            carrier: info for carrier, info in filtered_carrier_data_for_viz.items()
            if carrier in selected_carriers
        }
    else:
        network_source_data = filtered_carrier_data_for_viz

    if not network_source_data:
        if selected_carriers:
            st.info("No data available for the selected carriers after applying global filters.")
        else:
            st.info("Upload data and apply filters to see the network visualization.")
    else:
        # Set directed=True to indicate flow, and notebook=True for Streamlit embedding
        net = Network(height="750px", width="100%", directed=True, notebook=True)
        net.toggle_physics(True)

        added_nodes = set()

        # Add nodes and edges based on filtered data
        for carrier, info in network_source_data.items():
            # Add Carrier node
            if carrier not in added_nodes:
                net.add_node(carrier, label=carrier, color=node_colors['carrier'], shape=node_shapes['carrier'], title=f"Carrier: {carrier}")
                added_nodes.add(carrier)

            # Add Relationship Owners and edges (Owner -> Carrier)
            for owner in info['relationship owner']:
                if owner not in added_nodes:
                    net.add_node(owner, label=owner, color=node_colors['owner'], shape=node_shapes['owner'], title=f"Relationship Owner: {owner}")
                    added_nodes.add(owner)
                # Edge from owner to carrier, with visible label
                net.add_edge(owner, carrier, label="Relationship owner", title="Relationship owner", color="#DC3545", arrows='to') 

            # Add Brokers To and edges (Carrier -> Broker To)
            for broker_to in info['Brokers to']:
                if broker_to not in added_nodes:
                    net.add_node(broker_to, label=broker_to, color=node_colors['broker_to'], shape=node_shapes['broker_to'], title=f"Broker (To): {broker_to}")
                    added_nodes.add(broker_to)
                # Edge from carrier to broker_to, with visible label
                net.add_edge(carrier, broker_to, label="Brokers to", title="Brokers to", color="#007BFF", arrows='to')

            # Add Brokers Through and edges (Carrier -> Broker Through)
            for broker_through in info['Brokers through']:
                if broker_through not in added_nodes:
                    net.add_node(broker_through, label=broker_through, color=node_colors['broker_through'], shape=node_shapes['broker_through'], title=f"Broker (Through): {broker_through}")
                    added_nodes.add(broker_through)
                # Edge from carrier to broker_through, with visible label
                net.add_edge(carrier, broker_through, label="Brokers through", title="Brokers through", color="#28A745", arrows='to')

            # Add Broker Entities and edges (Carrier -> Broker Entity)
            for entity in info['broker entity of']:
                if entity not in added_nodes:
                    net.add_node(entity, label=entity, color=node_colors['entity'], shape=node_shapes['entity'], title=f"Broker Entity: {entity}")
                    added_nodes.add(entity)
                # Edge from carrier to entity, with visible label
                net.add_edge(carrier, entity, label="Broker entity of", title="Broker entity of", color="#FFC107", arrows='to')

        try:
            path = "/tmp/pyvis_graph.html"
            net.save_graph(path)
            with open(path, 'r', encoding='utf-8') as html_file:
                html_content = html_file.read()
            components.html(html_content, height=750)
        except Exception as e:
            st.error(f"Could not generate network graph: {e}. Ensure pyvis is installed and accessible.")
            st.info("If running locally, try: `pip install pyvis`")
            st.info("If on Streamlit Cloud, add `pyvis` to your `requirements.txt`.")


# --- Initial Message when no file is uploaded ---
else:
    st.info("⬆️ Please upload your Carrier Relationships file (CSV or Excel) in the sidebar to begin analysis.")
    st.markdown("---")