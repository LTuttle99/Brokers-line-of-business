import streamlit as st
import pandas as pd
import io

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
        2. Use the search bar or dropdown to find a specific Carrier.
        3. View the detailed relationship information in the main area.
        4. Download the displayed details for the selected carrier.
        """
    )
    st.write("---") # Separator within the expander
    st.write("Developed with Streamlit.")


# --- Caching Data Loading and Processing ---
# Use st.cache_data to cache the DataFrame and processed data
# This will prevent reloading and reprocessing the file on every interaction
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

    carrier_data = {}
    all_brokers_to = set()
    all_brokers_through = set()
    all_broker_entities = set()
    all_relationship_owners = set()

    for index, row in df.iterrows():
        carrier = str(row['Carrier']).strip() if pd.notna(row['Carrier']) else "Unnamed Carrier"
        
        if not carrier: # Treat truly empty strings as "Unnamed Carrier" for processing
            carrier = "Unnamed Carrier"

        # Skip row if carrier is still 'Unnamed Carrier' and there's no useful data in other key columns
        if carrier == "Unnamed Carrier" and all(pd.isna(row[col]) or not str(row[col]).strip() for col in expected_columns[1:]):
            continue

        if carrier not in carrier_data:
            carrier_data[carrier] = {
                'Brokers to': set(),
                'Brokers through': set(),
                'broker entity of': set(),
                'relationship owner': set()
            }

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
        for key in data_dict:
            carrier_data[carrier][key] = sorted(list(data_dict[key]))

    return df, carrier_data, all_brokers_to, all_brokers_through, all_broker_entities, all_relationship_owners

# --- Conditional execution based on file upload ---
if uploaded_file is not None:
    file_type = uploaded_file.name.split('.')[-1]
    df, carrier_data, all_brokers_to, all_brokers_through, all_broker_entities, all_relationship_owners = load_and_process_data(uploaded_file, file_type)

    unique_carriers = sorted(list(carrier_data.keys()))

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
    st.header("Select a Carrier")
    
    # Search bar
    search_query = st.text_input("Type to search for a Carrier:", "").strip()

    # Filter carriers based on search query
    filtered_carriers = [
        carrier for carrier in unique_carriers
        if search_query.lower() in carrier.lower()
    ]
    
    # Sort filtered carriers alphabetically
    filtered_carriers = sorted(filtered_carriers)

    if not filtered_carriers and search_query:
        st.warning(f"No carriers found matching '{search_query}'.")
        selected_carrier = "--- Select a Carrier ---" # Reset selection if no match
    else:
        selected_carrier = st.selectbox(
            "✨ Choose a Carrier from the list:",
            options=["--- Select a Carrier ---"] + filtered_carriers,
            index=0 # Default to the "Select a Carrier" option
        )
    st.markdown("---")

    # --- DISPLAY RESULTS ---
    if selected_carrier != "--- Select a Carrier ---":
        st.subheader(f"📊 Details for **{selected_carrier}**:")
        if selected_carrier in carrier_data:
            carrier_info = carrier_data[selected_carrier]

            # Use columns for better layout
            col_detail1, col_detail2 = st.columns(2)
            col_detail3, col_detail4 = st.columns(2)

            with col_detail1:
                st.markdown("#### 👉 Brokers To:")
                if carrier_info['Brokers to']:
                    for broker in carrier_info['Brokers to']:
                        st.markdown(f"- **{broker}**")
                else:
                    st.info("No 'Brokers to' information found for this carrier.")

            with col_detail2:
                st.markdown("#### 🤝 Brokers Through:")
                if carrier_info['Brokers through']:
                    for broker in carrier_info['Brokers through']:
                        st.markdown(f"- **{broker}**")
                else:
                    st.info("No 'Brokers through' information found for this carrier.")

            with col_detail3:
                st.markdown("#### 🏢 Broker Entity Of:")
                if carrier_info['broker entity of']:
                    for entity in carrier_info['broker entity of']:
                        st.markdown(f"- **{entity}**")
                else:
                    st.info("No 'broker entity of' information found for this carrier.")

            with col_detail4:
                st.markdown("#### 👤 Relationship Owner:")
                if carrier_info['relationship owner']:
                    for owner in carrier_info['relationship owner']:
                        st.markdown(f"- **{owner}**")
                else:
                    st.info("No 'relationship owner' information found for this carrier.")

            st.markdown("---")

            # --- DOWNLOAD BUTTON ---
            # Create a small DataFrame for the selected carrier's details for download
            download_df = pd.DataFrame({
                "Carrier": [selected_carrier],
                "Brokers to": [", ".join(carrier_info['Brokers to'])],
                "Brokers through": [", ".join(carrier_info['Brokers through'])],
                "broker entity of": [", ".join(carrier_info['broker entity of'])],
                "relationship owner": [", ".join(carrier_info['relationship owner'])]
            })

            # Convert DataFrame to CSV string
            csv_string = download_df.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label=f"⬇️ Download Details for {selected_carrier}",
                data=csv_string,
                file_name=f"{selected_carrier}_relationships.csv",
                mime="text/csv",
                help="Download the displayed information for the selected carrier as a CSV file."
            )


        else:
            st.warning(f"Data for '**{selected_carrier}**' not found after processing. Please check your file data.")
    else:
        st.info("⬆️ Please upload your file and select a carrier from the dropdown above to view their details.")

# --- Initial Message when no file is uploaded ---
else:
    st.info("⬆️ Please upload your Carrier Relationships file (CSV or Excel) in the sidebar to begin analysis.")