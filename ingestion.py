import os
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
from . import config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_tlc_links():
    """Scrapes the NYC TLC website to find all parquet file links."""
    logger.info(f"Scraping TLC website: {config.TLC_BASE_URL}")
    try:
        response = requests.get(config.TLC_BASE_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.endswith('.parquet') and ('yellow' in href or 'green' in href):
                full_url = href if href.startswith('http') else urljoin(config.TLC_BASE_URL, href)
                links.append(full_url)
        
        logger.info(f"Found {len(links)} parquet links.")
        return links
    except Exception as e:
        logger.error(f"Failed to scrape TLC website: {e}")
        return []

def download_file(url, dest_path):
    """Downloads a file with retry logic."""
    if os.path.exists(dest_path):
        logger.info(f"File already exists: {dest_path}")
        return True

    logger.info(f"Downloading {url} to {dest_path}")
    retries = 3
    for attempt in range(retries):
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            logger.info(f"Download complete: {dest_path}")
            return True
        except Exception as e:
            logger.warning(f"Attempt {attempt+1}/{retries} failed: {e}")
            time.sleep(2)
    
    logger.error(f"Failed to download {url} after {retries} attempts.")
    return False

def get_expected_files(year):
    """Generates a list of expected filenames for a given year."""
    types = ['yellow', 'green']
    months = range(1, 13)
    expected = []
    for t in types:
        for m in months:
            expected.append(f"{t}_tripdata_{year}-{m:02d}.parquet")
    return expected

def run_ingestion():
    """Main ingestion flow."""
    logger.info("Starting Data Ingestion Phase...")
    
    # Ensure raw directory exists
    os.makedirs(config.RAW_DATA_DIR, exist_ok=True)
    
    # Scrape links
    all_links = fetch_tlc_links()
    
    # Target files for 2025
    expected_2025 = get_expected_files(config.TARGET_YEAR)
    
    # Also need Dec 2023 and Dec 2024 for imputation if Dec 2025 is missing
    imputation_files = [
        f"yellow_tripdata_2023-12.parquet", f"green_tripdata_2023-12.parquet",
        f"yellow_tripdata_2024-12.parquet", f"green_tripdata_2024-12.parquet"
    ]
    
    target_files = expected_2025 + imputation_files
    
    missing_files = []
    
    for filename in target_files:
        # Check if we have a link for this file
        # TLC links usually look like: .../yellow_tripdata_2024-01.parquet
        # We match by checking if the filename is in the url
        found_link = next((link for link in all_links if filename in link), None)
        
        dest_path = config.RAW_DATA_DIR / filename
        
        if found_link:
            download_file(found_link, dest_path)
        else:
            if "2025-12" in filename:
                logger.info(f"December 2025 data not found (as expected). Will assume imputation needed.")
                missing_files.append(filename)
            elif "2025" in filename:
                 logger.warning(f"Missing data for {filename}. It might not be released yet.")
                 missing_files.append(filename)
            else:
                 logger.warning(f"Historical data {filename} not found in scraped links.")
                 
    # In a real scenario, we might want to fail if historical data is missing,
    # but for this challenge we proceed.
    
    logger.info("Ingestion complete.")
    return missing_files

if __name__ == "__main__":
    run_ingestion()
