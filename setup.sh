#!/bin/bash

# Setup script for Licensee Enrichment Portal

echo "Setting up Licensee Enrichment Portal..."

# Create virtual environment
echo "Creating virtual environment..."
python -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Setup Streamlit secrets
if [ ! -f .streamlit/secrets.toml ]; then
    echo "Creating Streamlit secrets file..."
    mkdir -p .streamlit
    cp .streamlit/secrets.toml.example .streamlit/secrets.toml
    echo "Please update .streamlit/secrets.toml with your API keys"
fi

echo "Setup complete! You can now run the application with:"
echo "streamlit run app_clean.py"