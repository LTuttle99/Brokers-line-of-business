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

# Initialize data container
df = None

if uploaded_file is not None:
    # Determine file type and read accordingly
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        else:
            st.sidebar.error("Unsupported file type. Please upload a .csv or .xlsx file.")
            st.stop()
        st.sidebar.success("File uploaded and read successfully!")
    except Exception as e:
        st.sidebar.error(f"Error reading file: {e}. Please ensure it's a valid .csv or .xlsx file.")
        st.stop()

    # --- DATA PROCESSING ---
    # Clean column names (strip whitespace)
    df.columns = df.columns.str.strip()

    # Expected columns based on our discussion
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

    # Create a dictionary to store all relationships for quick lookup
    # Key: Carrier Name
    # Value: Dictionary containing lists of "Brokers to", "Brokers through", etc.
    carrier_data = {}

    for index, row in df.iterrows():
        carrier = str(row['Carrier']).strip() if pd.notna(row['Carrier']) else "Unnamed Carrier"
        
        # Ensure carrier is a valid string, not empty after stripping
        if not carrier:
            carrier = "Unnamed Carrier"
            
        # Skip row if carrier is still 'Unnamed Carrier' and there's no useful data
        if carrier == "Unnamed Carrier" and all(pd.isna(row[col]) or not str(row[col]).strip() for col in expected_columns[1:]):
            continue

        # Initialize carrier entry if it doesn't exist
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

        # Process 'Brokers through'
        brokers_through_val = str(row['Brokers through']).strip() if pd.notna(row['Brokers through']) else ""
        if brokers_through_val:
            for broker in [b.strip() for b in brokers_through_val.split(',') if b.strip()]:
                carrier_data[carrier]['Brokers through'].add(broker)

        # Process 'broker entity of' - Assuming this is not comma-separated, single value per row
        broker_entity_val = str(row['broker entity of']).strip() if pd.notna(row['broker entity of']) else ""
        if broker_entity_val:
            carrier_data[carrier]['broker entity of'].add(broker_entity_val)

        # Process 'relationship owner' - Assuming this is not comma-separated, single value per row
        relationship_owner_val = str(row['relationship owner']).strip() if pd.notna(row['relationship owner']) else ""
        if relationship_owner_val:
            carrier_data[carrier]['relationship owner'].add(relationship_owner_val)

    # Convert sets to sorted lists for display
    for carrier, data_dict in carrier_data.items():
        for key in data_dict:
            carrier_data[carrier][key] = sorted(list(data_dict[key]))

    # Get unique sorted list of carriers for the dropdown
    unique_carriers = sorted(list(carrier_data.keys()))

    # --- CARRIER SELECTION ---
    st.header("Select a Carrier")
    selected_carrier = st.selectbox(
        "✨ Choose a Carrier to view its associated brokers and details:",
        options=["--- Select a Carrier ---"] + unique_carriers, # Improved default option
        index=0
    )
    st.markdown("---")

    # --- DISPLAY RESULTS ---
    if selected_carrier != "--- Select a Carrier ---":
        st.subheader(f"📊 Details for **{selected_carrier}**:")
        if selected_carrier in carrier_data:
            carrier_info = carrier_data[selected_carrier]

            # Use columns for better layout
            col1, col2 = st.columns(2)
            col3, col4 = st.columns(2) # New columns for the last two fields

            with col1:
                st.markdown("#### 👉 Brokers To:")
                if carrier_info['Brokers to']:
                    for broker in carrier_info['Brokers to']:
                        st.markdown(f"- **{broker}**")
                else:
                    st.info("No 'Brokers to' information found for this carrier.")

            with col2:
                st.markdown("#### 🤝 Brokers Through:")
                if carrier_info['Brokers through']:
                    for broker in carrier_info['Brokers through']:
                        st.markdown(f"- **{broker}**")
                else:
                    st.info("No 'Brokers through' information found for this carrier.")

            with col3:
                st.markdown("#### 🏢 Broker Entity Of:")
                if carrier_info['broker entity of']:
                    for entity in carrier_info['broker entity of']:
                        st.markdown(f"- **{entity}**")
                else:
                    st.info("No 'broker entity of' information found for this carrier.")

            with col4:
                st.markdown("#### 👤 Relationship Owner:")
                if carrier_info['relationship owner']:
                    for owner in carrier_info['relationship owner']:
                        st.markdown(f"- **{owner}**")
                else:
                    st.info("No 'relationship owner' information found for this carrier.")

        else:
            st.warning(f"Data for '**{selected_carrier}**' not found after processing. Please check your file data.")
    else:
        st.info("⬆️ Please upload your file and select a carrier from the dropdown above to view their details.")

# --- Initial Message when no file is uploaded ---
else:
    st.info("⬆️ Please upload your Carrier Relationships file (CSV or Excel) in the sidebar to begin analysis.")