import streamlit as st
import pandas as pd
import io
import plotly.express as px

# --- SET UP STREAMLIT PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Carrier Relationship Viewer",
    layout="wide", # Use 'wide' layout for more space
    initial_sidebar_state="expanded"
    # To add custom themes, create a .streamlit/config.toml file in your project root
    # with content like:
    # [theme]
    # primaryColor="#FF4B4B"
    # backgroundColor="#FFFFFF"
    # secondaryBackgroundColor="#F0F2F6"
    # textColor="#303030"
    # font="sans serif"
)

st.title("🔍 Carrier Relationship Viewer")
st.markdown("---") # Add a separator for visual appeal
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
    st.write("---") # Separator within the expander
    st.write("Developed with Streamlit.")

# --- IN-APP SAMPLE FILE DOWNLOAD ---
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
    help="Download a sample CSV file with the correct column headers."
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
        st.stop() # Stop execution if columns are missing

    # --- Data Aggregation for carrier_data dictionary ---
    carrier_data = {}
    all_brokers_to = set()
    all_brokers_through = set()
    all_broker_entities = set()
    all_relationship_owners = set()

    for index, row in df.iterrows():
        carrier = str(row['Carrier']).strip() if pd.notna(row['Carrier']) else "Unnamed Carrier"
        
        if not carrier: # Treat truly empty strings as "Unnamed Carrier" for processing
            carrier = "Unnamed Carrier"

        if carrier == "Unnamed Carrier" and all(pd.isna(row[col]) or not str(row[col]).strip() for col in expected_columns[1:]):
            continue # Skip fully empty or unnamed carrier rows

        if carrier not in carrier_data:
            carrier_data[carrier] = {
                'Brokers to': set(),
                'Brokers through': set(),
                'broker entity of': set(),
                'relationship owner': set(),
                'original_rows': [] # To store original rows for global filtering and details
            }
        
        carrier_data[carrier]['original_rows'].append(index) # Store row index for later filtering

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
    selected_filter_brokers_to = st.sidebar.multiselect(
        "Filter by 'Brokers to'",
        options=sorted(list(all_brokers_to))
    )
    selected_filter_brokers_through = st.sidebar.multiselect(
        "Filter by 'Brokers through'",
        options=sorted(list(all_brokers_through))
    )
    selected_filter_broker_entity = st.sidebar.multiselect(
        "Filter by 'broker entity of'",
        options=sorted(list(all_broker_entities))
    )
    selected_filter_relationship_owner = st.sidebar.multiselect(
        "Filter by 'relationship owner'",
        options=sorted(list(all_relationship_owners))
    )

    # Apply global filters to narrow down the list of carriers for selection
    filtered_unique_carriers_for_selection = []
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
    
    # Sort filtered carriers again for good measure
    filtered_unique_carriers_for_selection = sorted(filtered_unique_carriers_for_selection)

    # --- SUMMARY STATISTICS ---
    st.markdown("## 📈 Data Overview")
    col_count1, col_count2, col_count3, col_count4, col_count5 = st.columns(5)

    with col_count1:
        st.metric(label="Total Unique Carriers", value=len(unique_carriers))
    with col_count2:
        st.metric(label="Unique 'Brokers to'", value=len(all_brokers_to))
    with col_count3:
        st.metric(label="Unique 'Brokers through'", value=len(all_brokers_through))
    with col_count4:
        st.metric(label="Unique Broker Entities", value=len(all_broker_entities))
    with col_count5:
        st.metric(label="Unique Relationship Owners", value=len(all_relationship_owners))
    st.markdown("---")

    # --- CARRIER SEARCH AND SELECTION ---
    st.header("Select Carrier(s) for Details")
    
    # Search bar
    search_query = st.text_input("Type to search for a Carrier:", "").strip()

    # Filter carriers based on search query AND global filters
    search_filtered_carriers = [
        carrier for carrier in filtered_unique_carriers_for_selection
        if search_query.lower() in carrier.lower()
    ]
    
    if not search_filtered_carriers and search_query:
        st.warning(f"No carriers found matching '{search_query}' with current filters.")
        selected_carriers = [] # No carriers selected if no match
    else:
        # Multi-select for carriers
        selected_carriers = st.multiselect(
            "✨ Choose one or more Carriers from the filtered list:",
            options=search_filtered_carriers,
            default=[] # No default selected
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
            'carrier_specific_details': {} # Store individual carrier details here
        }
        
        download_rows = []

        for carrier in selected_carriers:
            if carrier in carrier_data:
                info = carrier_data[carrier]
                
                # Aggregate for combined display
                combined_details['Brokers to'].update(info['Brokers to'])
                combined_details['Brokers through'].update(info['Brokers through'])
                combined_details['broker entity of'].update(info['broker entity of'])
                combined_details['relationship owner'].update(info['relationship owner'])

                # Store details for individual display and download
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
                        st.markdown("**Brokers To:**")
                        if info['Brokers to']:
                            for broker in info['Brokers to']:
                                st.markdown(f"- {broker}")
                        else:
                            st.markdown("*(None)*")

                    with col_ind2:
                        st.markdown("**Brokers Through:**")
                        if info['Brokers through']:
                            for broker in info['Brokers through']:
                                st.markdown(f"- {broker}")
                        else:
                            st.markdown("*(None)*")
                    
                    with col_ind3:
                        st.markdown("**Broker Entity Of:**")
                        if info['broker entity of']:
                            for entity in info['broker entity of']:
                                st.markdown(f"- {entity}")
                        else:
                            st.markdown("*(None)*")

                    with col_ind4:
                        st.markdown("**Relationship Owner:**")
                        if info['relationship owner']:
                            for owner in info['relationship owner']:
                                st.markdown(f"- {owner}")
                        else:
                            st.markdown("*(None)*")
                    
                    if carrier_idx < len(selected_carriers) - 1: # Add a separator between individual carriers
                        st.markdown("---")
            st.markdown("---")


        # --- DOWNLOAD BUTTON ---
        download_df = pd.DataFrame(download_rows)
        csv_string = download_df.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label=f"⬇️ Download Details for Selected Carriers ({len(selected_carriers)})",
            data=csv_string,
            file_name=f"selected_carriers_relationships.csv",
            mime="text/csv",
            help="Download the displayed information for the selected carriers as a CSV file."
        )

    else:
        st.info("⬆️ Please upload your file and select one or more carriers from the dropdown above to view their details.")

    # --- VISUALIZATIONS ---
    st.markdown("---")
    st.markdown("## 📊 Relationship Visualizations")

    # Bar chart for Top Brokers To
    brokers_to_counts = pd.Series([b for carrier_info in carrier_data.values() for b in carrier_info['Brokers to']])
    if not brokers_to_counts.empty:
        top_brokers_to = brokers_to_counts.value_counts().reset_index()
        top_brokers_to.columns = ['Broker', 'Count']
        fig_brokers_to = px.bar(
            top_brokers_to.head(10), # Show top 10
            x='Broker',
            y='Count',
            title='Top 10 "Brokers To" by Carrier Associations',
            labels={'Broker': 'Broker (To)', 'Count': 'Number of Carriers'},
            height=400
        )
        st.plotly_chart(fig_brokers_to, use_container_width=True)
    else:
        st.info("No 'Brokers to' data available for visualization.")

    # Bar chart for Top Brokers Through
    brokers_through_counts = pd.Series([b for carrier_info in carrier_data.values() for b in carrier_info['Brokers through']])
    if not brokers_through_counts.empty:
        top_brokers_through = brokers_through_counts.value_counts().reset_index()
        top_brokers_through.columns = ['Broker', 'Count']
        fig_brokers_through = px.bar(
            top_brokers_through.head(10), # Show top 10
            x='Broker',
            y='Count',
            title='Top 10 "Brokers Through" by Carrier Associations',
            labels={'Broker': 'Broker (Through)', 'Count': 'Number of Carriers'},
            height=400
        )
        st.plotly_chart(fig_brokers_through, use_container_width=True)
    else:
        st.info("No 'Brokers through' data available for visualization.")

    # Bar chart for Relationship Owners Distribution
    relationship_owners_counts = pd.Series([o for carrier_info in carrier_data.values() for o in carrier_info['relationship owner']])
    if not relationship_owners_counts.empty:
        owner_distribution = relationship_owners_counts.value_counts().reset_index()
        owner_distribution.columns = ['Owner', 'Count']
        fig_owners = px.bar(
            owner_distribution,
            x='Owner',
            y='Count',
            title='Distribution of Relationship Owners',
            labels={'Owner': 'Relationship Owner', 'Count': 'Number of Carriers'},
            height=400
        )
        st.plotly_chart(fig_owners, use_container_width=True)
    else:
        st.info("No 'Relationship Owner' data available for visualization.")


# --- Initial Message when no file is uploaded ---
else:
    st.info("⬆️ Please upload your Carrier Relationships file (CSV or Excel) in the sidebar to begin analysis.")
    st.markdown("---")
    st.markdown("### Or, download a sample file to get started:")
    # This section is duplicated from sidebar to be visible when no file is uploaded
    sample_data_download = {
        'Carrier': ['Carrier A', 'Carrier B', 'Carrier C', 'Carrier D', 'Carrier E'],
        'Brokers to': ['Broker Alpha, Broker Beta', 'Broker Gamma', 'Broker Delta', '', 'Broker Zeta'],
        'Brokers through': ['Broker 123', 'Broker 456, Broker 789', 'Broker 010', 'Broker 111', ''],
        'broker entity of': ['Entity X', 'Entity Y', 'Entity Z', 'Entity X', 'Entity Y'],
        'relationship owner': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown', 'John Doe']
    }
    sample_df_download = pd.DataFrame(sample_data_download)
    csv_sample_download = sample_df_download.to_csv(index=False).encode('utf-8')

    st.download_button(
        label="⬇️ Download Sample Data File",
        data=csv_sample_download,
        file_name='Sample Carrier Relationships.csv',
        mime='text/csv',
        help="Download a sample CSV file with the correct column headers."
    )