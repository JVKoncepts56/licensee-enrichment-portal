# Licensee Enrichment Portal

A Streamlit application for automating licensee data enrichment, processing, and database storage.

## Features

- **Single Entry Processing**: Manual input of licensee information with real-time enrichment
- **Batch Processing**: Upload CSV files with multiple licensee records for bulk processing
- **AI-Powered Enrichment**: Uses OpenAI's GPT-4o to analyze websites and provide detailed business insights
- **Category Matching**: Automatically identifies relevant product categories
- **Text Summaries**: Generates strategic, market, and audience summaries
- **Vector Embeddings**: Creates embeddings for semantic search capabilities
- **Supabase Integration**: Stores all processed data in your Supabase database

## Setup Instructions

### Prerequisites

- Python 3.7+
- OpenAI API key
- Supabase account and API credentials

### Quick Installation

Use our setup script for automated installation:

```bash
chmod +x setup.sh
./setup.sh
```

### Manual Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your Streamlit secrets:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   
4. Edit `.streamlit/secrets.toml` with your actual API keys:
   ```toml
   OPENAI_API_KEY = "your-openai-api-key"
   SUPABASE_URL = "your-supabase-url"
   SUPABASE_KEY = "your-supabase-key"
   ```

### Supabase Database Setup

Ensure your Supabase database has a table called `licensees` with the following fields:

- `id` (auto-generated)
- `uid` (text, unique identifier)
- `brand_name` (text)
- `contact` (text)
- `website` (text)
- `headquarters` (text)
- Various enriched fields (see app_clean.py for complete list)
- Embedding fields (vector type)

### Running the Application Locally

Start the Streamlit app with:

```bash
streamlit run app_clean.py
```

## Usage

### Single Entry Processing

1. Fill out the form with licensee information (UUID and website URL are required)
2. Click "Process Licensee Data"
3. View the enriched data and generated summaries
4. Download results as CSV if needed

### Batch Processing

1. Prepare a CSV file with the required columns: uid, brand_name, website, etc.
2. Upload the CSV file in the "Batch Upload" tab
3. Click "Process Batch"
4. Monitor the progress as each record is processed
5. View the results table showing success/failure status for each record

## Deployment Options

### Streamlit Cloud (Recommended)

The easiest way to deploy the application for team use:

1. Create a GitHub repository with your code
2. Connect to Streamlit Cloud: https://streamlit.io/cloud
3. Configure your secrets in the Streamlit Cloud dashboard
4. Deploy the application

See `deploy_streamlit_cloud.md` for detailed instructions.

### Docker Deployment

For containerized deployment:

1. Build the Docker image:
   ```bash
   docker build -t licensee-portal .
   ```

2. Run the container:
   ```bash
   docker run -p 8501:8501 -e OPENAI_API_KEY=your-api-key -e SUPABASE_URL=your-url -e SUPABASE_KEY=your-key licensee-portal
   ```

3. Access the application at http://localhost:8501

### Google App Engine Deployment

To deploy to Google App Engine:

1. Install Google Cloud SDK
2. Authenticate with gcloud:
   ```bash
   gcloud auth login
   ```

3. Set your project:
   ```bash
   gcloud config set project your-project-id
   ```

4. Deploy the app:
   ```bash
   gcloud app deploy
   ```

## Maintenance

### Adding New Features

If you need to extend the application:

1. Modify `app_clean.py` to add new features
2. Update the Supabase database schema if needed
3. Update the documentation to reflect changes
4. Redeploy the application

### Updating Dependencies

To update dependencies:

1. Update `requirements.txt`
2. Rebuild/redeploy the application

## License

[Your license information here]# licensee-enrichment-portal
# licensee-enrichment-portal
# licensee-enrichment-portal
