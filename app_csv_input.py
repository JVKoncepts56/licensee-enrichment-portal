import streamlit as st
import pandas as pd
import uuid
import openai
import json
import time
from supabase import create_client

# Page config
st.set_page_config(page_title="Licensee Enrichment Portal", layout="wide")

# Function to process a single licensee - can be used for both single and batch processing
def process_licensee(uid, brand_name, contact_name, email, website, headquarters, 
                     supabase_url, supabase_key, openai_api_key, category_list):
    """
    Process a single licensee entry - handles enrichment, embedding, and Supabase upload
    Returns a dictionary with the processed data and status
    """
    # Initialize result dictionary
    result = {
        "success": False,
        "message": "",
        "data": {}
    }
    
    try:
        # Initialize OpenAI
        openai.api_key = openai_api_key
        
        # Prepare website URL
        if not website.startswith(('http://', 'https://')):
            website = 'https://' + website
            
        # Call OpenAI for enrichment
        prompt = f"""You are analyzing a brand based on its official website. Prioritize extracting insights from the website before relying on the brand name.

Brand website: {website}
Brand name: {brand_name}

TASK 1: ANALYZE COMPANY INFORMATION
First, provide a detailed analysis of the brand based on the website and your knowledge.

TASK 2: DETERMINE HEADQUARTERS LOCATION
Based on the website domain, your knowledge of the brand, and any context clues, determine the most likely headquarters location for this company. If the headquarters location is not specified in the input, you must make your best educated guess. Consider:
- Domain TLD (.com, .co.uk, etc.)
- Company history
- Known locations of similar brands
- Industry trends

IMPORTANT: DO NOT return an error message. Instead, use your training knowledge about this website and brand. You have been trained on vast amounts of internet data up until your knowledge cutoff, so use that knowledge to analyze this brand rather than trying to access the live website.

You MUST provide substantive answers for all fields based on your prior knowledge, even if you cannot currently browse the website. If it's a known brand or website, provide detailed information from your training. If it's completely unknown, provide reasonable guesses based on the domain name, brand name, and any other contextual clues.

Based on this information, return the following structured data. Format the output exactly as shown, with each key followed by a colon on the same line. Do not skip any fields. Do not add commentary.

business_category: What type of business are they in? (e.g., Fashion, Sportswear, Consumer Goods, Tech)
age_group: Classify their main buyer by age range (e.g., 18–25, 25–35, etc.)
audience_description: Describe the brand's audience and its most ravenous buyers in one sentence
industry_classification: NAICS or SIC-style classification (write the industry name, not the number)
popular_products_or_services: List the top two most purchased or known-for products/services
price_positioning: Budget, Mid-Tier, Premium, or Luxury
brand_affinity_competitors: Who is their biggest competitor or most similar brand?
retail_distribution_channels: List the top retail or distribution channels (e.g., Amazon, Walmart, DTC)
countries_distributed: Choose the top 3 countries they sell into from this list ONLY: USA, Canada, China, Mexico, United Kingdom, France, Germany, Taiwan
primary_licensing_category: From their product types, what is the single strongest licensing category (1 only)?
secondary_licensing_category: From their product types, what is the next most relevant licensing category (1 only)?
known_licensing_agreements: Name up to 3 known licensing agreements the brand has been involved in — where the brand either (1) licensed its name to another company to create products, or (2) licensed another brand/IP to put onto their own products. These must be real brand-to-brand licensing agreements and should only include products that were actually sold.
product_summary_text: Write one paragraph summarizing the types of products they are known for and where they are being sold most effectively. This will be used to match categories."""

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        
        # Parse response
        raw_text = response.choices[0].message.content
        raw_text = raw_text.replace('\r\n', '\n').strip()
        output = raw_text.split('\n')
        
        # Parse fields
        raw_map = {}
        current_key = None
        summary_started = False
        summary_lines = []
        
        for line in output:
            if ":" not in line:
                if summary_started and current_key:
                    summary_lines.append(line.strip())
                continue
                
            parts = line.split(":", 1)
            if len(parts) == 2:
                current_key = parts[0].strip().lower()
                value = parts[1].strip()
                
                if current_key == "product_summary_text":
                    summary_started = True
                    summary_lines.append(value)
                else:
                    raw_map[current_key] = value
        
        if summary_lines:
            raw_map["product_summary_text"] = " ".join(summary_lines)
        
        # Category matching
        summary_text = raw_map.get("product_summary_text", "").lower()
        
        # Calculate scores
        import re
        scores = []
        for cat in category_list:
            cat_lower = cat.lower()
            regex = r'(?:^|\W)' + re.escape(cat_lower) + r'(?:$|\W)'
            count = len(re.findall(regex, summary_text))
            scores.append({"category": cat, "count": count})
        
        # Sort by count
        scores.sort(key=lambda x: x["count"], reverse=True)
        
        # Override categories
        if scores and scores[0]["count"] > 0:
            raw_map["primary_licensing_category"] = scores[0]["category"]
        if len(scores) > 1 and scores[1]["count"] > 0:
            raw_map["secondary_licensing_category"] = scores[1]["category"]
        
        # Generate summaries
        brand_full = brand_name
        
        # Basic summaries
        summaries = {
            "audience_summary": f"This company targets {raw_map.get('age_group', 'N/A')} consumers, focusing on {raw_map.get('business_category', 'N/A')} across {raw_map.get('countries_distributed', 'N/A')}. {raw_map.get('audience_description', 'N/A')}",
            
            "product_summary": f"They specialize in {raw_map.get('popular_products_or_services', 'N/A')}, with licensing focus areas in {raw_map.get('primary_licensing_category', 'N/A')} and {raw_map.get('secondary_licensing_category', 'N/A')}.",
            
            "market_fit_summary": f"Distributed across {raw_map.get('countries_distributed', 'N/A')}, their products are positioned as {raw_map.get('price_positioning', 'N/A')} offerings through {raw_map.get('retail_distribution_channels', 'N/A')} channels.",
            
            "competitive_summary": f"Compared to {raw_map.get('brand_affinity_competitors', 'other players') if raw_map.get('brand_affinity_competitors') else 'other players'}, they differentiate by focusing on {raw_map.get('industry_classification', 'N/A')} with notable licensing agreements including {raw_map.get('known_licensing_agreements', 'N/A')}.",
            
            "combined_summary": f"{brand_name} is a company specializing in {raw_map.get('popular_products_or_services', 'N/A')} ({raw_map.get('primary_licensing_category', 'N/A')} and {raw_map.get('secondary_licensing_category', 'N/A')}) distributed across {raw_map.get('countries_distributed', 'N/A')}. They target {raw_map.get('age_group', 'N/A')} consumers ({raw_map.get('audience_description', 'N/A')}) through {raw_map.get('retail_distribution_channels', 'N/A')} channels, offering {raw_map.get('price_positioning', 'N/A')} products. Competitively, they stand out versus {raw_map.get('brand_affinity_competitors', 'N/A')} by focusing on {raw_map.get('industry_classification', 'N/A')} with key licensing agreements like {raw_map.get('known_licensing_agreements', 'N/A')}."
        }
        
        # Commentary fields
        opportunity_commentary = f"Based on {brand_full}'s focus on {raw_map.get('business_category', 'their industry')}, they show potential for licensing opportunities in the {raw_map.get('primary_licensing_category', 'primary')} and {raw_map.get('secondary_licensing_category', 'secondary')} categories. Their target demographic of {raw_map.get('age_group', 'consumers')} aligns with current market trends, and their existing distribution across {raw_map.get('countries_distributed', 'markets')} suggests capacity for expanded licensing partnerships."
        
        market_readiness = f"{brand_full} demonstrates market readiness through their established {raw_map.get('price_positioning', '')} positioning and presence in {raw_map.get('retail_distribution_channels', 'retail channels')}. Their experience with {raw_map.get('known_licensing_agreements', 'licensing agreements')} indicates familiarity with licensing processes. Their current position in the {raw_map.get('industry_classification', 'industry')} market provides a foundation for licensing expansion."
        
        audience_harmony = f"The harmony between {brand_full}'s products and their target audience of {raw_map.get('age_group', 'consumers')} is evident in their specialization in {raw_map.get('popular_products_or_services', 'products/services')}. Their understanding of {raw_map.get('audience_description', 'their audience')} enables them to create products that resonate with consumer preferences and lifestyle needs in the {raw_map.get('primary_licensing_category', 'licensing')} category."
        
        competitive_strength = f"In comparison to {raw_map.get('brand_affinity_competitors', 'competitors')}, {brand_full} differentiates through their focus on {raw_map.get('industry_classification', 'their classification')}. Their strength in {raw_map.get('primary_licensing_category', 'primary category')} positions them uniquely in the market. Their {raw_map.get('price_positioning', 'price point')} strategy gives them competitive advantage with their target {raw_map.get('age_group', 'demographic')} across {raw_map.get('countries_distributed', 'their markets')}."
        
        strategic_fit = f"{brand_full} exhibits strategic fit for licensing opportunities through their established brand identity in {raw_map.get('business_category', 'their category')}, market presence across {raw_map.get('countries_distributed', 'markets')}, and experience with {raw_map.get('known_licensing_agreements', 'licensing')}. Their focus on {raw_map.get('primary_licensing_category', 'primary')} and {raw_map.get('secondary_licensing_category', 'secondary')} categories allows for natural brand extensions that would resonate with their {raw_map.get('age_group', 'target audience')}."
        
        # Add to summaries
        summaries["opportunity_alignment_commentary"] = opportunity_commentary
        summaries["market_readiness_commentary"] = market_readiness
        summaries["audience_harmony_analysis"] = audience_harmony
        summaries["competitive_strength_analysis"] = competitive_strength
        summaries["strategic_fit_commentary"] = strategic_fit
        
        # Generate embeddings
        embeddings = {}
        
        # List of fields that need embeddings
        text_fields = [
            ("combined_strategic_summary", summaries.get("combined_summary", "")),
            ("opportunity_alignment_score_commentary", summaries.get("opportunity_alignment_commentary", "")),
            ("market_readiness_commentary", summaries.get("market_readiness_commentary", "")),
            ("audience_product_harmony_analysis", summaries.get("audience_harmony_analysis", "")),
            ("competitive_strength_analysis", summaries.get("competitive_strength_analysis", "")),
            ("strategic_fit_commentary", summaries.get("strategic_fit_commentary", ""))
        ]
        
        # Generate embeddings for each field
        for field_name, text in text_fields:
            embedding_name = f"{field_name}_embedding"
            
            # Skip if text is empty
            if not text.strip():
                embeddings[embedding_name] = None
                continue
            
            try:
                embedding_response = openai.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text
                )
                embeddings[embedding_name] = embedding_response.data[0].embedding
            except Exception as e:
                print(f"Error generating {embedding_name}: {e}")
                embeddings[embedding_name] = None
        
        # Prepare data for Supabase
        licensee_data = {
            "uid": uid,
            "brand_name": brand_name,
            "contact": contact_name,
            "website": website,
            "headquarters": headquarters or "Unknown",
            # Enriched fields
            "business_category": raw_map.get("business_category", "N/A"),
            "age_group": raw_map.get("age_group", "N/A"),
            "audience_description": raw_map.get("audience_description", "N/A"),
            "industry_classification": raw_map.get("industry_classification", "N/A"),
            "popular_type_of_product": raw_map.get("popular_products_or_services", "N/A"),
            "price_positioning": raw_map.get("price_positioning", "N/A"),
            "brand_competitors": raw_map.get("brand_affinity_competitors", "N/A"),
            "retail_distribution_channel": raw_map.get("retail_distribution_channels", "N/A"),
            "countries_distributed": raw_map.get("countries_distributed", "N/A"),
            "primary_licensing_category": raw_map.get("primary_licensing_category", "N/A"),
            "secondary_licensing_category": raw_map.get("secondary_licensing_category", "N/A"),
            "known_licensing_agreements": raw_map.get("known_licensing_agreements", "N/A"),
            "product": raw_map.get("product_summary_text", "N/A"),
            # Summaries
            "audience_summary": summaries.get("audience_summary", "N/A"),
            "product_summary": summaries.get("product_summary", "N/A"),
            "market_fit_summary": summaries.get("market_fit_summary", "N/A"),
            "competitive_differentiation_summary": summaries.get("competitive_summary", "N/A"),
            "combined_strategic_summary": summaries.get("combined_summary", "N/A"),
            # Additional commentary fields
            "opportunity_alignment_score_commentary": summaries.get("opportunity_alignment_commentary", ""),
            "market_readiness_commentary": summaries.get("market_readiness_commentary", ""),
            "audience_product_harmony_analysis": summaries.get("audience_harmony_analysis", ""),
            "competitive_strength_analysis": summaries.get("competitive_strength_analysis", ""),
            "strategic_fit_commentary": summaries.get("strategic_fit_commentary", ""),
            # Embeddings
            "combined_strategic_summary_embedding": embeddings.get("combined_strategic_summary_embedding"),
            "opportunity_alignment_score_commentary_embedding": embeddings.get("opportunity_alignment_score_commentary_embedding"),
            "market_readiness_commentary_embedding": embeddings.get("market_readiness_commentary_embedding"),
            "audience_product_harmony_analysis_embedding": embeddings.get("audience_product_harmony_analysis_embedding"),
            "competitive_strength_analysis_embedding": embeddings.get("competitive_strength_analysis_embedding"),
            "strategic_fit_commentary_embedding": embeddings.get("strategic_fit_commentary_embedding")
        }
        
        # Upload to Supabase
        supabase = create_client(supabase_url, supabase_key)
        
        # First check if record already exists
        existing_records = supabase.table("licensees").select("*").filter("uid", "eq", uid).execute()
        
        if existing_records.data and len(existing_records.data) > 0:
            # Update existing record
            existing_id = existing_records.data[0]["id"] if "id" in existing_records.data[0] else None
            if existing_id:
                result = supabase.table("licensees").update(licensee_data).filter("id", "eq", existing_id).execute()
                result_message = f"Updated existing record with ID: {existing_id}"
            else:
                # If there's no id, fall back to UID
                result = supabase.table("licensees").update(licensee_data).filter("uid", "eq", uid).execute()
                result_message = f"Updated existing record with UID: {uid}"
        else:
            # Insert new record
            result = supabase.table("licensees").insert(licensee_data).execute()
            result_message = f"Added new record with UID: {uid}"
        
        # Record success
        result = {
            "success": True,
            "message": result_message,
            "data": licensee_data,
            "raw_enrichment": raw_map,
            "summaries": summaries
        }
        
        return result
        
    except Exception as e:
        result["success"] = False
        result["message"] = str(e)
        return result

# App title and description
st.title("Licensee Enrichment Portal")
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

# Category list for matching (from your original script)
category_list = ["Accessories", "Sunglasses", "Scarves", "Belts", "Baseball Caps", "Beanies", "Tote Bags", "Backpacks", "Clutches", 
                 "Crossbody Bags", "Bags", "Mini Backpacks", "Wallets", "Lunch Bags / Lunch Kits", "Hair Accessories", "Hats", 
                 "Keychains", "Jewelry", "Temporary Tattoos", "Body Jewelry", "Buckles & Accessories", "Ties / Bowties", "Gloves", 
                 "Kids Socks", "Adults Socks", "Optical Glasses", "Kids Underwear", "Adult Underwear", "Kids Watches", "Adult Watches", 
                 "Watch Accessories", "Kids Luggage", "Adult Luggage", "Travel Accessories", "Pins", "Umbrellas", "Iron-On Patches", 
                 "Apparel", "Men's T-Shirts", "Men's Shirts", "Men's Jeans", "Men's Jackets", "Men's Suits", "Men's Activewear", 
                 "Women's Dresses", "Women's Tops", "Women's Skirts", "Women's Leggings", "Women's Blazers", "Women's Maternity Wear", 
                 "Boys' Apparel", "Girls' Apparel", "School Uniforms", "Kids Activewear", "Women's Activewear", "Boy's Pajamas", 
                 "Girl's Pajamas", "Women's Pajamas", "Men's Pajamas", "Kids Jackets", "Kids Onesies", "Adult Onesies", 
                 "Women's Jackets", "Men's Pants", "Kids Sweaters", "Adult Sweaters", "Kids Hoodies", "Adult Hoodies", 
                 "Boy's Swimwear", "Girl's Swimwear", "Women's Swimwear", "Men's Swimwear", "Kids Bathrobes", "Adult Bathrobes", 
                 "Kids Raincoats", "Adult Raincoats", "Scrubs", "Domestics", "Bed Sheets", "Duvet Covers", "Pillowcases", 
                 "Comforters", "Bath Towels", "Hand Towels", "Beach Towels", "Bath Mats", "Outdoor Rugs", "Bedding Sets", 
                 "Blankets / Throws", "Weighted Blankets", "Throw Pillows", "Body Pillows", "Shower Curtains", "Cushions", 
                 "Bathroom Accessories", "Indoor Rugs", "Curtains", "Electronics & Accessories", "Phone cases", "Wall Chargers", 
                 "Wireless Chargers", "Car Chargers", "Portable chargers", "Backpack", "Messenger Bags", "Briefcases", 
                 "Rolling Laptop Bags", "Tablet Cases & Sleeves", "Laptop Cases & Sleeves", "Laptop Accessories", "Laptop Bags", 
                 "Kids Tablets", "Smartwatches", "Fitness Trackers", "Wearable Tech", "Speakers", "Gaming Accessories", 
                 "Gaming Controllers", "USB Memory Sticks", "Headphones", "Electronic Cables", "Footwear", "Men's Sneakers", 
                 "Men's Dress Shoes", "Men's Boots", "Men's Sandals", "Women's Flats", "Women's Heels", "Women's Sandals", 
                 "Women's Athletic Shoes", "Kids Sneakers", "Kids School Shoes", "Kids Boots", "Kids Sandals", "Women's Sneakers", 
                 "Men's Athletic Shoes", "Women's Boots", "Kids Athletic Shoes", "Men's Slippers", "Women's Slippers", 
                 "Kids Slippers", "Men's Flipflops", "Women's Flipflops", "Kids Flipflops", "Kids Rain Boots", "Adult Rain Boots"]

# Create tabs for Single Entry vs Batch Upload
tab1, tab2, tab3 = st.tabs(["Single Entry", "Batch Upload", "CSV Text Input"])

with tab1:
    # Form inputs for single entry
    with st.form("licensee_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            uid = st.text_input("UUID (Required)", help="Enter the unique identifier for this licensee")
            brand_name = st.text_input("Brand Name")
            contact_name = st.text_input("Contact Name (Optional)")
        
        with col2:
            email = st.text_input("Email Address")
            website = st.text_input("Company Website URL")
            headquarters = st.text_input("Headquarters Location (Optional)")
        
        submit = st.form_submit_button("Process Licensee Data")

with tab2:
    st.write("### Batch Upload")
    st.write("Upload a CSV file with multiple licensees to process in batch.")
    
    # Sample CSV template
    st.write("#### CSV Format:")
    df_sample = pd.DataFrame({
        "uid": ["abc123", "def456"],
        "brand_name": ["Brand 1", "Brand 2"],
        "contact": ["Contact 1", "Contact 2"],
        "email": ["email1@example.com", "email2@example.com"],
        "website": ["https://example1.com", "https://example2.com"],
        "headquarters": ["New York, USA", "London, UK"]
    })
    
    st.dataframe(df_sample)
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    # Process batch button
    batch_submit = st.button("Process Batch")

with tab3:
    st.write("### CSV Text Input")
    st.write("Enter your CSV data directly in the text area below.")
    
    # Sample CSV template
    st.write("#### CSV Format Example:")
    sample_csv = """uid,brand_name,contact,email,website,headquarters
abc123,Brand 1,Contact 1,email1@example.com,example1.com,New York USA
def456,Brand 2,Contact 2,email2@example.com,example2.com,London UK"""
    
    # Text area for CSV input
    csv_text = st.text_area("Enter CSV data", height=200, 
                           help="Paste your CSV data here. Make sure the first row contains headers.")
    
    # Process CSV text button
    csv_text_submit = st.button("Process CSV Text")
    
    # Process CSV text
    if csv_text_submit and csv_text:
        try:
            # Convert text to DataFrame
            from io import StringIO
            csv_data = StringIO(csv_text)
            df = pd.read_csv(csv_data)
            
            st.write("### Parsed CSV Data:")
            st.dataframe(df)
            
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
                    row_contact = row.get("contact", "")
                    row_email = row.get("email", "")
                    row_website = row.get("website", "")
                    row_headquarters = row.get("headquarters", "")
                    
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
                        # Process this row
                        result = process_licensee(
                            uid=row_uid,
                            brand_name=row_brand_name,
                            contact_name=row_contact,
                            email=row_email,
                            website=row_website,
                            headquarters=row_headquarters,
                            supabase_url=supabase_url,
                            supabase_key=supabase_key,
                            openai_api_key=openai_api_key,
                            category_list=category_list
                        )
                        
                        # Add to results
                        results_list.append({
                            "uid": row_uid,
                            "brand_name": row_brand_name,
                            "status": "Success" if result["success"] else f"Failed - {result['message']}",
                            "enriched": result["success"]
                        })
                        
                        if result["success"]:
                            success_count += 1
                        else:
                            failed_count += 1
                            
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
                    
                    # Add a small delay to avoid rate limits
                    time.sleep(0.5)
            
            # Final progress update
            progress_bar.progress(1.0)
            status_text.text(f"Processing complete: {success_count} succeeded, {failed_count} failed")
            
            # Final success message
            if success_count > 0:
                st.success(f"Successfully processed {success_count} licensees!")
            if failed_count > 0:
                st.warning(f"Failed to process {failed_count} licensees. See results table for details.")
        
        except Exception as e:
            st.error(f"Error processing CSV text: {str(e)}")

# Handle single entry form submission
if submit:
    # Validation
    if not uid:
        st.error("UUID is required. Please enter a valid UUID.")
        st.stop()
        
    if not website:
        st.error("Website URL is required. Please enter a valid website URL.")
        st.stop()

    # Create dedicated containers for the process logs and results
    with st.container():
        st.subheader("Processing Log")
        process_log = st.empty()
        log_content = "Starting licensee enrichment process...\n"
        log_content += f"✅ Using provided UUID: {uid}\n"
        log_content += f"📊 Processing licensee data...\n"
        process_log.code(log_content, language="bash")
        
    # Process with spinner
    with st.spinner("Enriching licensee data..."):
        # Process the licensee
        process_result = process_licensee(
            uid=uid,
            brand_name=brand_name,
            contact_name=contact_name,
            email=email,
            website=website,
            headquarters=headquarters,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            openai_api_key=openai_api_key,
            category_list=category_list
        )
        
        # Update process log
        if process_result["success"]:
            log_content += f"✅ {process_result['message']}\n"
            log_content += "\n--- RECORD DETAILS ---\n"
            log_content += f"UID: {uid}\n"
            log_content += f"Brand Name: {brand_name}\n"
            log_content += f"Business Category: {process_result['data'].get('business_category')}\n"
            log_content += f"Primary Licensing Category: {process_result['data'].get('primary_licensing_category')}\n"
            log_content += f"Secondary Licensing Category: {process_result['data'].get('secondary_licensing_category')}\n"
            log_content += f"Countries: {process_result['data'].get('countries_distributed')}\n"
            log_content += "------------------------\n\n"
            log_content += "✅ ENRICHMENT COMPLETE ✅\n"
            process_log.code(log_content, language="bash")
            
            # Display results
            st.success(f"Successfully processed {brand_name}!")
            
            # Display enriched data
            st.subheader("Enriched Data")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Input Information:**")
                st.write(f"**Brand Name:** {brand_name}")
                st.write(f"**Contact:** {contact_name}")
                st.write(f"**Email:** {email}")
                st.write(f"**Website:** {website}")
                st.write(f"**UUID:** {uid}")
            
            with col2:
                st.write("**Business Information:**")
                st.write(f"**Category:** {process_result['data'].get('business_category')}")
                st.write(f"**Industry:** {process_result['data'].get('industry_classification')}")
                st.write(f"**Target Age:** {process_result['data'].get('age_group')}")
                st.write(f"**Pricing:** {process_result['data'].get('price_positioning')}")
            
            # Display summaries
            with st.expander("View Generated Summaries"):
                for summary_name, summary_text in process_result["summaries"].items():
                    st.write(f"**{summary_name.replace('_', ' ').title()}:**")
                    st.write(summary_text)
                    st.write("---")
            
            # Option to download as CSV
            csv_data = pd.DataFrame([process_result["data"]])
            csv = csv_data.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name=f"licensee_{uid}.csv",
                mime="text/csv"
            )
        else:
            log_content += f"❌ Error: {process_result['message']}\n"
            process_log.code(log_content, language="bash")
            st.error(f"Error processing: {process_result['message']}")

# Handle batch processing from file upload
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
                row_contact = row.get("contact", "")
                row_email = row.get("email", "")
                row_website = row.get("website", "")
                row_headquarters = row.get("headquarters", "")
                
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
                    # Process this row
                    result = process_licensee(
                        uid=row_uid,
                        brand_name=row_brand_name,
                        contact_name=row_contact,
                        email=row_email,
                        website=row_website,
                        headquarters=row_headquarters,
                        supabase_url=supabase_url,
                        supabase_key=supabase_key,
                        openai_api_key=openai_api_key,
                        category_list=category_list
                    )
                    
                    # Add to results
                    results_list.append({
                        "uid": row_uid,
                        "brand_name": row_brand_name,
                        "status": "Success" if result["success"] else f"Failed - {result['message']}",
                        "enriched": result["success"]
                    })
                    
                    if result["success"]:
                        success_count += 1
                    else:
                        failed_count += 1
                        
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
                
                # Add a small delay to avoid rate limits
                time.sleep(0.5)
        
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
    1. Enter the licensee's information:
       - UUID (required): A unique identifier for this licensee
       - Brand Name: The name of the brand
       - Website URL: The brand's website (required)
       - Other fields as available
       
    2. Click 'Process Licensee Data' to start the enrichment process
    
    3. The system will:
       - Generate a unique ID for the licensee
       - Analyze the company website
       - Create detailed business profiles and summaries
       - Generate embeddings for similarity matching
       - Store all data in your Supabase database
       
    4. For batch processing:
       - Prepare a CSV file with the required columns
       - Upload the file and click 'Process Batch'
       - Monitor progress as each record is processed
       
    5. For direct CSV input:
       - Paste your CSV data in the text area
       - Click 'Process CSV Text'
       - Monitor progress as each record is processed
    """)