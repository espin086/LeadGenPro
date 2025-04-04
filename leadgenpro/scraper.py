"""
Core scraper functionality for LeadGenPro
"""
import re
import time
import random
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

import requests
import pandas as pd
from bs4 import BeautifulSoup
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("leadgenpro")

# Create data directory if not exists
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# List of User-Agent strings for rotating
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0'
]

class ContactInfo(BaseModel):
    url: str
    emails: List[str] = []
    phone_numbers: List[str] = []
    all_text: Optional[str] = None

def scrape_google_search(query: str, location: str, start: int = 0) -> Optional[str]:
    """
    Scrape Google search results for a given query and location.
    """
    query = query.strip().replace(' ', '+')
    location = location.strip().replace(' ', '+')

    url = f'https://www.google.com/search?q={query}+{location}&start={start}&num=10'

    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.google.com/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        logger.info(f"Google search status code: {response.status_code}")
        
        if response.status_code == 200:
            # Log the URLs found in response headers to debug any redirects
            if response.history:
                for resp in response.history:
                    logger.info(f"Redirect: {resp.url} -> {resp.headers.get('Location')}")
            
            return response.text
        elif response.status_code == 403:
            logger.warning(f"Error 403: Forbidden - Access denied for {url}")
            logger.warning("Google may be blocking the request. Try changing the User-Agent or using a proxy.")
        else:
            logger.warning(f"Failed to retrieve the page. Status code: {response.status_code}")
    except requests.exceptions.Timeout:
        logger.error(f"Request for {url} timed out after 30 seconds")
    except Exception as e:
        logger.error(f"An error occurred while scraping Google: {e}")

    return None

def extract_emails_from_content(content: str) -> List[str]:
    """Extract email addresses from text content."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?!png|jpg|jpeg|gif|svg|webp)[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, content)
    return list(set(emails)) if emails else []

def extract_phone_numbers_from_content(content: str) -> List[str]:
    """Extract phone numbers from text content."""
    phone_pattern = r'\(?\b[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}\b'
    phone_numbers = re.findall(phone_pattern, content)
    return list(set(phone_numbers)) if phone_numbers else []

def extract_all_text(content: str) -> str:
    """Extract all visible text from HTML content."""
    soup = BeautifulSoup(content, 'html.parser')

    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()

    # Extract and return the visible text
    text = soup.get_text(separator=' ', strip=True)
    return text if text else "No text found"

def get_page_content(url: str) -> Optional[str]:
    """Get HTML content from a URL."""
    try:
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Referer': 'https://www.google.com/'
        }
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.text
        else:
            logger.warning(f"Failed to retrieve {url}, Status code: {response.status_code}")
            return None
    except requests.exceptions.Timeout:
        logger.error(f"Request for {url} timed out after 30 seconds")
        return None
    except Exception as e:
        logger.error(f"An error occurred while processing {url}: {e}")
        return None

def process_urls_for_contact_info(urls: List[str]) -> List[ContactInfo]:
    """Process a list of URLs and extract contact information."""
    results = []
    
    if not urls:
        logger.warning("No URLs provided to process for contact info")
        return results
    
    for i, url in enumerate(urls):
        try:
            logger.info(f"Processing URL {i+1}/{len(urls)}: {url}")
            
            sleep_delay = random.uniform(2, 4)
            logger.info(f"Sleeping for {sleep_delay:.2f} seconds before processing {url}")
            time.sleep(sleep_delay)  # Sleep for 2-4 seconds to avoid rate limiting
            
            content = get_page_content(url)
            
            if content:
                logger.info(f"Successfully retrieved content from {url} (length: {len(content)} chars)")
                emails = extract_emails_from_content(content)
                logger.info(f"Found {len(emails)} emails on {url}: {emails}")
                
                phone_numbers = extract_phone_numbers_from_content(content)
                logger.info(f"Found {len(phone_numbers)} phone numbers on {url}: {phone_numbers}")
                
                all_text = extract_all_text(content)
                text_preview = all_text[:100] + "..." if all_text and len(all_text) > 100 else all_text
                logger.info(f"Extracted text preview from {url}: {text_preview}")
                
                results.append(ContactInfo(
                    url=url,
                    emails=emails,
                    phone_numbers=phone_numbers,
                    all_text=all_text
                ))
            else:
                logger.warning(f"Failed to retrieve content from {url}")
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            # Continue with the next URL rather than failing the entire process
            continue
    
    return results

def extract_urls(text: str) -> List[str]:
    """Extract URLs from text."""
    # More comprehensive URL pattern
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*(?:\?\S*)?'
    urls = set(re.findall(url_pattern, text))
    
    # Add additional logging
    logger.info(f"Raw URLs extracted: {urls}")
    
    return list(urls)

def clean_urls(urls: List[str]) -> List[str]:
    """Clean and deduplicate URLs."""
    cleaned_urls = []
    for url in urls:
        fixed_url = fix_malformed_url(url)
        if fixed_url not in cleaned_urls:
            cleaned_urls.append(fixed_url)
    
    logger.info(f"Cleaned URLs: {cleaned_urls}")
    return cleaned_urls

def fix_malformed_url(url: str) -> str:
    """Fix malformed URLs."""
    url = url.replace('\\', '')
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    valid_url_pattern = re.compile(r'(https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')
    match = valid_url_pattern.match(url)
    if match:
        return match.group(0)
    return url

def filter_urls(urls: List[str], exclude_terms: List[str]) -> List[str]:
    """Filter out URLs containing excluded terms."""
    # Log before filtering
    logger.info(f"Filtering URLs with exclude terms: {exclude_terms}")
    
    # Track which URLs get filtered and why
    for url in urls:
        for term in exclude_terms:
            if term in url:
                logger.info(f"Excluding URL {url} because it contains term: {term}")
    
    filtered_urls = [url for url in urls if not any(term in url for term in exclude_terms)]
    logger.info(f"After exclude filtering: {filtered_urls}")
    
    truncated_urls = [truncate_url(url) for url in filtered_urls]
    return truncated_urls

def truncate_url(url: str) -> str:
    """Truncate URL to domain level."""
    domain_endings = ['.com', '.org', '.net', '.edu', '.gov', '.io', '.info', '.business', '.dental']
    for ending in domain_endings:
        if ending in url:
            return url.split(ending)[0] + ending
    return url

def sanitize_string(input_string: str) -> str:
    """Sanitize a string for use in filenames."""
    cleaned_string = input_string.strip().lower()
    cleaned_string = re.sub(r'[^a-zA-Z0-9]+', '_', cleaned_string)
    return cleaned_string

def save_to_csv(data: List[ContactInfo], query: str, location: str) -> str:
    """Save contact information to a CSV file and return the file path."""
    # Convert ContactInfo objects to dictionaries
    data_dicts = [
        {
            "URL": item.url,
            "Emails": ", ".join(item.emails) if item.emails else "No email found",
            "Phone Numbers": ", ".join(item.phone_numbers) if item.phone_numbers else "No phone number found",
            "All Text": item.all_text
        }
        for item in data
    ]
    
    df = pd.DataFrame(data_dicts)
    cleaned_query = sanitize_string(query)
    cleaned_location = sanitize_string(location)
    file_name = f"{cleaned_query}_{cleaned_location}_contact_info.csv"
    file_path = data_dir / file_name
    
    df.to_csv(file_path, index=False)
    logger.info(f"Data has been saved to {file_path}")
    
    return str(file_path)

async def scrape_and_process(
    job_id: str,
    query: str,
    location: str,
    results: int,
    jobs_dict: Dict[str, Dict[str, Any]]
) -> None:
    """
    Background task to scrape Google and process the results.
    """
    try:
        # Update job status
        jobs_dict[job_id]["status"] = "processing"
        
        all_results = ""
        
        # Scrape Google search results
        for i in range(0, results, 10):
            logger.info(f"Scraping results for start={i}")
            result = scrape_google_search(query=query, location=location, start=i)
            
            if result:
                all_results += result
                # Log a small sample of the raw HTML to help debug
                logger.debug(f"Sample of raw HTML: {result[:500]}...")
            else:
                logger.warning(f"Failed to retrieve results for start={i}")

            sleep_time = random.uniform(2, 5)
            logger.info(f"Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        # Extract and process URLs
        result_urls = extract_urls(all_results)
        logger.info(f"Number of URLs extracted: {len(result_urls)}")
        
        cleaned_urls = clean_urls(result_urls)
        
        # Use a more targeted exclude list
        exclude_terms = ['google.com/search', 'gstatic.com', 'google.com/imgres']
        filtered_urls = filter_urls(cleaned_urls, exclude_terms)
        logger.info(f"Number of filtered URLs: {len(filtered_urls)}")

        # Process URLs to extract contact information
        contact_info = process_urls_for_contact_info(filtered_urls)
        logger.info(f"Number of URLs processed for contact info: {len(contact_info)}")

        # Save results to CSV
        file_path = save_to_csv(contact_info, query, location)
        
        # Import here to avoid circular imports
        from leadgenpro.api import ScrapeResult
        
        # Update job with results
        jobs_dict[job_id].update({
            "status": "completed",
            "result": ScrapeResult(
                query=query,
                location=location,
                results=results,
                contact_info=contact_info,
                file_path=file_path
            )
        })
        
    except Exception as e:
        logger.error(f"Error in background task: {e}")
        jobs_dict[job_id].update({
            "status": "failed",
            "error": str(e)
        }) 