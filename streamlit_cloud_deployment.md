# Deploying to Streamlit Cloud

## Prerequisites
- GitHub account
- Repository with your Streamlit app

## Step 1: Push your code to GitHub
After creating a GitHub repository, push your local code to GitHub with:

```bash
# Replace YOUR-USERNAME with your GitHub username
git remote add origin https://github.com/YOUR-USERNAME/licensee-enrichment-portal.git
git push -u origin main
```

## Step 2: Sign in to Streamlit Cloud
1. Go to https://streamlit.io/cloud
2. Sign in with your GitHub account

## Step 3: Deploy your app
1. Click on "New app"
2. Select your repository (licensee-enrichment-portal)
3. Select the main branch
4. For the Main file path, enter: `app_csv_input.py`
5. Click "Deploy"

## Step 4: Configure secrets
1. After deployment, you'll need to set up your secrets
2. In your app's dashboard, click on the three-dot menu and select "Settings"
3. Go to "Secrets"
4. Add your secrets in TOML format:

```toml
OPENAI_API_KEY = "your-openai-api-key"
SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-supabase-key"
```

5. Click "Save"

## Step 5: Finalize deployment
1. Your app will automatically redeploy with the new settings
2. Once deployed, you'll get a public URL like:
   `https://yourusername-licensee-enrichment-portal.streamlit.app`
3. Share this URL with your team members to access the app

## Managing your app
- **Updates**: Simply push new changes to your GitHub repository's main branch
- **Monitor usage**: In the app dashboard, you can see usage statistics
- **Troubleshoot**: View logs by clicking on the three-dot menu and selecting "Logs"