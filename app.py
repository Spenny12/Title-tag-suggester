import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from google import genai

# --- STREAMLIT UI SETUP ---
st.set_page_config(page_title="SEO Title Generator", page_icon="📝", layout="wide")

st.title("📝 Strict Length SEO Title Generator")
st.write("Upload a CSV of URLs, and this tool will crawl the pages and generate optimized titles strictly between **50 and 60 characters**.")

# Sidebar for configuration
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")
st.sidebar.markdown("[Get a free Gemini API Key here](https://aistudio.google.com/)")

# --- CORE FUNCTIONS ---
def scrape_page_content(url):
    """Crawls the URL and extracts the main visible text."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script, style, and navigation elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        return text[:3000] # Limit to 3000 chars to focus on primary content
    except Exception as e:
        return None

def generate_strict_title(client, current_title, page_content, url):
    """Generates a title and strictly enforces the 50-60 character limit via validation loops."""
    if not page_content:
        return "Could not crawl page content."

    max_retries = 3
    for attempt in range(max_retries):
        prompt = f"""
        You are an expert SEO copywriter. I need a new title tag for a webpage.
        
        Current Title: "{current_title}"
        URL: {url}
        Page Content Snippet: "{page_content}"
        
        CRITICAL RULES:
        1. The new title MUST be between 50 and 60 characters long (including spaces).
        2. Count the characters carefully before outputting.
        3. Do not include your character count in the output.
        4. Return ONLY the new title text. No quotation marks, no intro text.
        """
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            suggested_title = response.text.strip().replace('"', '')
            char_count = len(suggested_title)
            
            # Strict length validation
            if 50 <= char_count <= 60:
                return suggested_title
        except Exception as e:
            return f"API Error: {e}"
            
    return f"Failed constraint after {max_retries} tries. Best effort: {suggested_title}"

# --- APP LOGIC ---
uploaded_file = st.file_uploader("Upload CSV File (Must have 'URL' and 'Current Title' columns)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # Validation checks on CSV schema
    if 'URL' not in df.columns or 'Current Title' not in df.columns:
        st.error("Error: CSV must contain exactly 'URL' and 'Current Title' columns.")
    else:
        st.write("### Preview of Uploaded Data", df.head())
        
        # Run processing when button is clicked
        if st.button("Generate Titles", disabled=not api_key):
            if not api_key:
                st.warning("Please enter your Gemini API key in the sidebar first.")
            else:
                try:
                    # Initialize client with user provided key
                    client = genai.Client(api_key=api_key)
                except Exception as e:
                    st.error(f"Failed to initialize Gemini Client: {e}")
                    st.stop()

                suggested_titles = []
                title_lengths = []
                
                # Progress bars for user feedback
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                total_rows = len(df)
                
                for index, row in df.iterrows():
                    url = row['URL']
                    current_title = row['Current Title']
                    
                    status_text.text(f"Processing ({index + 1}/{total_rows}): {url}")
                    
                    content = scrape_page_content(url)
                    new_title = generate_strict_title(client, current_title, content, url)
                    
                    suggested_titles.append(new_title)
                    title_lengths.append(len(new_title))
                    
                    # Update progress bar
                    progress_bar.progress((index + 1) / total_rows)
                
                status_text.text("Processing complete!")
                
                # Append results to the dataframe
                df['Suggested Title'] = suggested_titles
                df['Suggested Length'] = title_lengths
                
                # Display results
                st.write("### Processed Results")
                st.dataframe(df)
                
                # Create a download button for the new CSV
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Optimized CSV",
                    data=csv_data,
                    file_name="optimized_seo_titles.csv",
                    mime="text/csv"
                )
        elif not api_key:
            st.info("← Please enter your Gemini API Key in the sidebar to enable processing.")
