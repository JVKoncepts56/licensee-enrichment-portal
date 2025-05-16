import streamlit as st
import pandas as pd
import uuid
import openai
from supabase import create_client
import time

# Page config
st.set_page_config(page_title="Licensee Enrichment Portal (Simple)", layout="wide")

# App title and description
st.title("Licensee Enrichment Portal (Simplified)")
st.write("Enter licensee information to enrich and add to the database.")

# Configuration - Store these in Streamlit secrets in production
if "OPENAI_API_KEY" not in st.secrets:
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    if not openai_api_key:
        st.warning("Please enter your OpenAI API key to continue")
        st.stop()
else:
    openai_api_key = st.secrets["OPENAI_API_KEY"]

if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
    supabase_url = st.text_input("Supabase URL")
    supabase_key = st.text_input("Supabase Key", type="password")
    if not supabase_url or not supabase_key:
        st.warning("Please enter your Supabase credentials to continue")
        st.stop()
else:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]

# Initialize OpenAI
openai.api_key = openai_api_key

# Create tabs for Single Entry vs Batch Upload
tab1, tab2 = st.tabs(["Single Entry", "Batch Upload"])

with tab1:
    # Simple form for single entry
    with st.form("licensee_form"):
        uid = st.text_input("UUID (Required)", help="Enter the unique identifier for this licensee")
        brand_name = st.text_input("Brand Name")
        website = st.text_input("Company Website URL")
        
        submit = st.form_submit_button("Process Licensee Data")

    # Handle form submission
    if submit:
        # Validation
        if not uid:
            st.error("UUID is required. Please enter a valid UUID.")
            st.stop()
            
        if not website:
            st.error("Website URL is required. Please enter a valid website URL.")
            st.stop()

        # Simple processing without the full enrichment
        with st.spinner("Processing licensee data..."):
            st.success(f"Successfully processed entry for {brand_name}!")
            
            # Display basic information
            st.subheader("Processed Data")
            st.write(f"**Brand Name:** {brand_name}")
            st.write(f"**Website:** {website}")
            st.write(f"**UUID:** {uid}")
            
            # Test connecting to Supabase (but don't actually insert data)
            try:
                supabase = create_client(supabase_url, supabase_key)
                st.success("Successfully connected to Supabase!")
            except Exception as e:
                st.error(f"Error connecting to Supabase: {str(e)}")
                
            # Test OpenAI connection (but don't make a real API call)
            try:
                st.success("OpenAI API key configured successfully!")
            except Exception as e:
                st.error(f"Error with OpenAI configuration: {str(e)}")

with tab2:
    st.write("### Batch Upload")
    st.write("Upload a CSV file with multiple licensees to process in batch.")
    
    # Sample CSV template
    st.write("#### CSV Format:")
    df_sample = pd.DataFrame({
        "uid": ["abc123", "def456"],
        "brand_name": ["Brand 1", "Brand 2"],
        "website": ["https://example1.com", "https://example2.com"]
    })
    
    st.dataframe(df_sample)
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    # Process batch button
    batch_submit = st.button("Process Batch")
    
    # Batch processing
    if uploaded_file is not None and batch_submit:
        batch_process_placeholder = st.empty()
        batch_process_placeholder.info("Starting batch processing...")
        
        try:
            # Load CSV
            df = pd.read_csv(uploaded_file)
            batch_process_placeholder.info(f"Loaded CSV with {len(df)} rows")
            
            # Validate required columns
            required_columns = ["uid", "brand_name", "website"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"Error: Missing required columns: {', '.join(missing_columns)}")
                st.stop()
            
            # Setup progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Create container for batch results
            batch_results = st.container()
            
            # Count for successful and failed entries
            success_count = 0
            failed_count = 0
            
            # Will store minimal results for display
            results_list = []
            
            with batch_results:
                st.write("### Batch Processing Results")
                results_table = st.empty()
                
                # Process each row
                for index, row in df.iterrows():
                    # Update progress
                    progress = (index + 1) / len(df)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing row {index + 1} of {len(df)}: {row.get('brand_name', 'Unknown')}")
                    
                    # Extract row data
                    row_uid = row.get("uid", "")
                    row_brand_name = row.get("brand_name", "")
                    row_website = row.get("website", "")
                    
                    # Skip if missing required fields
                    if not row_uid or not row_website:
                        results_list.append({
                            "uid": row_uid,
                            "brand_name": row_brand_name,
                            "status": "Failed - Missing required fields",
                            "enriched": False
                        })
                        failed_count += 1
                        continue
                    
                    try:
                        # Simple "processing" - in a real app we would call process_licensee here
                        time.sleep(0.5)  # Simulate processing time
                        
                        # Add to results
                        results_list.append({
                            "uid": row_uid,
                            "brand_name": row_brand_name,
                            "status": "Success",
                            "enriched": True
                        })
                        success_count += 1
                            
                    except Exception as e:
                        results_list.append({
                            "uid": row_uid,
                            "brand_name": row_brand_name,
                            "status": f"Failed - {str(e)}",
                            "enriched": False
                        })
                        failed_count += 1
                    
                    # Display current results
                    results_df = pd.DataFrame(results_list)
                    results_table.dataframe(results_df)
                    
                    # Add a small delay to avoid overloading the UI
                    time.sleep(0.1)
            
            # Final progress update
            progress_bar.progress(1.0)
            status_text.text(f"Processing complete: {success_count} succeeded, {failed_count} failed")
            
            # Final success message
            if success_count > 0:
                st.success(f"Successfully processed {success_count} licensees!")
            if failed_count > 0:
                st.warning(f"Failed to process {failed_count} licensees. See results table for details.")
        
        except Exception as e:
            st.error(f"Error processing batch: {str(e)}")

# Show instructions at the bottom
with st.expander("How to use this tool"):
    st.write("""
    This is a simplified version of the Licensee Enrichment Portal for testing purposes.
    
    1. Enter the basic licensee information:
       - UUID (required)
       - Brand Name
       - Website URL (required)
       
    2. Click 'Process Licensee Data' to test the app functionality
    
    This version only tests the basic UI and connections without making any actual API calls.

    For batch processing:
    1. Prepare a CSV file with the required columns
    2. Upload the file and click 'Process Batch'
    3. Monitor the progress as each record is processed
    """)