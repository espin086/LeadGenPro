import requests
import re
from bs4 import BeautifulSoup
import logging
import time
import random
import pandas as pd
import argparse
import csv

logging.basicConfig(level=logging.INFO)

# List of User-Agent strings for rotating
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0'
]

def scrape_google_search(query, location, start=0):
    """
    This function takes a query and a location, formats them for a Google Search URL,
    sends the request, and returns the HTML content of the search results.
    """
    query = query.strip().replace(' ', '+')
    location = location.strip().replace(' ', '+')

    url = f'https://www.google.com/search?q={query}+{location}&start={start}'

    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Referer': 'https://www.google.com/'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.text
        elif response.status_code == 403:
            logging.warning(f"Error 403: Forbidden - Access denied for {url}")
        else:
            logging.warning(f"Failed to retrieve the page. Status code: {response.status_code}")
    except requests.exceptions.Timeout:
        logging.error(f"Request for {url} timed out after 30 seconds")
    except Exception as e:
        logging.error(f"An error occurred while scraping Google: {e}")

    return None

def extract_emails_from_content(content):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?!png|jpg|jpeg|gif|svg|webp)[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, content)
    return list(set(emails)) if emails else None

def extract_phone_numbers_from_content(content):
    phone_pattern = r'\(?\b[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}\b'
    phone_numbers = re.findall(phone_pattern, content)
    return list(set(phone_numbers)) if phone_numbers else None

def extract_all_text(content):
    """
    Extract all visible text from the HTML content of a page.
    """
    soup = BeautifulSoup(content, 'html.parser')

    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()

    # Extract and return the visible text
    text = soup.get_text(separator=' ', strip=True)
    return text if text else "No text found"

def get_page_content(url):
    try:
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Referer': 'https://www.google.com/'
        }
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.text
        else:
            logging.warning(f"Failed to retrieve {url}, Status code: {response.status_code}")
            return None
    except requests.exceptions.Timeout:
        logging.error(f"Request for {url} timed out after 30 seconds")
        return None
    except Exception as e:
        logging.error(f"An error occurred while processing {url}: {e}")
        return None

def process_urls_for_contact_info(urls):
    """
    This function processes a list of URLs, extracts emails, phone numbers, and visible text,
    and returns a list containing the results for each URL.
    """
    results = []
    
    for url in urls:
        sleep_delay = random.uniform(2, 4)
        logging.info(f"Sleeping for {sleep_delay:.2f} seconds")
        time.sleep(sleep_delay)  # Sleep for 2-4 seconds to avoid rate limiting
        
        logging.info(f"Processing URL: {url}")
        
        content = get_page_content(url)
        
        if content:
            emails = extract_emails_from_content(content)
            phone_numbers = extract_phone_numbers_from_content(content)
            all_text = extract_all_text(content)
            
            formatted_emails = f'"{", ".join(emails)}"' if emails else "No email found"
            formatted_phone_numbers = f'"{", ".join(phone_numbers)}"' if phone_numbers else "No phone number found"
            
            results.append({
                "URL": url,
                "Emails": formatted_emails,
                "Phone Numbers": formatted_phone_numbers,
                "All Text": all_text
            })
    
    return results

def save_to_csv(data, query, location):
    df = pd.DataFrame(data)
    cleaned_query = sanitize_string(query)
    cleaned_location = sanitize_string(location)
    csv_file = f"data/{cleaned_query}_{cleaned_location}_contact_info.csv"
    df.to_csv(csv_file, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"Data has been saved to {csv_file}")

def truncate_url(url):
    domain_endings = ['.com', '.org', '.net', '.edu', '.gov', '.io', '.info', '.business', '.dental']
    for ending in domain_endings:
        if ending in url:
            return url.split(ending)[0] + ending
    return url

def filter_urls(urls, exclude_terms):
    filtered_urls = [url for url in urls if not any(term in url for term in exclude_terms)]
    truncated_urls = [truncate_url(url) for url in filtered_urls]
    return truncated_urls

def extract_urls(text):
    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
    urls = set(re.findall(url_pattern, text))
    return list(urls)

def clean_urls(urls):
    cleaned_urls = []
    for url in urls:
        fixed_url = fix_malformed_url(url)
        if fixed_url not in cleaned_urls:
            cleaned_urls.append(fixed_url)
    return cleaned_urls

def fix_malformed_url(url):
    url = url.replace('\\', '')
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    valid_url_pattern = re.compile(r'(https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')
    match = valid_url_pattern.match(url)
    if match:
        return match.group(0)
    return url

def sanitize_string(input_string):
    cleaned_string = input_string.strip().lower()
    cleaned_string = re.sub(r'[^a-zA-Z0-9]+', '_', cleaned_string)
    return cleaned_string

def main(query, location, results):
    all_results = ""
    
    for i in range(0, results, 10):
        logging.info(f"Scraping results for start={i}")
        result = scrape_google_search(query=query, location=location, start=i)
        
        if result:
            all_results += result
        else:
            logging.warning(f"Failed to retrieve results for start={i}")

        sleep_time = random.uniform(2, 5)
        logging.info(f"Sleeping for {sleep_time:.2f} seconds")
        time.sleep(sleep_time)
    
    logging.debug(all_results)
    logging.info(f"Number of results scraped: {len(all_results)}")

    result_urls = extract_urls(all_results)
    logging.debug(result_urls)
    logging.info(f"Number of URLs extracted: {len(result_urls)}")
    
    cleaned_urls = clean_urls(result_urls)
    exclude_terms = ['google', 'gstatic', 'usnews']
    filtered_urls = filter_urls(cleaned_urls, exclude_terms)
    logging.info(f"Number of filtered URLs: {len(filtered_urls)}")
    logging.debug(filtered_urls)

    contact_info = process_urls_for_contact_info(filtered_urls)
    logging.info(f"Number of URLs processed for contact info: {len(contact_info)}")
    logging.info(contact_info)

    save_to_csv(contact_info, query, location)


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Scrape Google Search Results for URLs, Emails, Phone Numbers, and All Text')
    parser.add_argument('query', type=str, help='The search query, e.g., "saunas"')
    parser.add_argument('location', type=str, help='The location for the search, e.g., "los angeles"')
    parser.add_argument('results', type=int, help='Number of results to scrape, must be a multiple of 10')

    # Parse the command line arguments
    args = parser.parse_args()

    # Call the main function with the parsed arguments
    main(args.query, args.location, args.results)