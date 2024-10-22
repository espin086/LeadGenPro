import requests
import re
from bs4 import BeautifulSoup
import logging
import time
import random
import pandas as pd

logging.basicConfig(level=logging.INFO)

# List of User-Agent strings for rotating
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0'
]

# Optional proxies for rotating IPs (uncomment if you want to use them)
# PROXIES = [
#     {'http': 'http://yourproxy1.com:port', 'https': 'https://yourproxy1.com:port'},
#     {'http': 'http://yourproxy2.com:port', 'https': 'https://yourproxy2.com:port'},
#     {'http': 'http://yourproxy3.com:port', 'https': 'https://yourproxy3.com:port'}
# ]

def extract_emails_from_url(url):
    """
    This function takes a URL, sends a request to the webpage,
    and returns any email addresses found on the page.
    """
    try:
        # Randomize User-Agent
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Referer': 'https://www.google.com/'  # Set referer to make it look like the request came from Google
        }

        # Send a GET request to the URL
        response = requests.get(url, headers=headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Parse the page content using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Use a regex pattern to find all email addresses
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, soup.text)
            
            # Return unique emails as a list
            return list(set(emails)) if emails else None
        else:
            logging.warning(f"Failed to retrieve {url}, Status code: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"An error occurred while processing {url}: {e}")
        return None

def process_urls_for_emails(urls):
    """
    This function takes a list of URLs, processes each one, and extracts emails.
    It returns a dictionary containing the URL and the emails found on each page.
    """
    results = {}
    
    for url in urls:
        sleep_delay = random.uniform(2, 4)
        logging.info(f"Sleeping for {sleep_delay:.2f} seconds")
        time.sleep(sleep_delay)  # Sleep for 2-4 seconds to avoid rate limiting
        logging.info(f"Processing URL: {url}")
        emails = extract_emails_from_url(url)
        if emails:
            results[url] = emails
        else:
            results[url] = "No email found"
    
    return results


def truncate_url(url):
    """
    This function truncates the URL after common domain endings (.com, .org, etc.)
    and removes any additional text after the domain.
    """
    domain_endings = ['.com', '.org', '.net', '.edu', '.gov', '.io', '.info', '.business', '.dental']
    
    for ending in domain_endings:
        if ending in url:
            return url.split(ending)[0] + ending
    
    return url

def filter_urls(urls, exclude_terms):
    """
    This function filters out URLs that contain any of the substrings in 'exclude_terms'.
    Then it truncates the remaining URLs after common domain endings.
    """
    filtered_urls = [url for url in urls if not any(term in url for term in exclude_terms)]
    
    truncated_urls = [truncate_url(url) for url in filtered_urls]
    
    return truncated_urls

def fix_malformed_url(url):
    """
    This function fixes common malformed URLs by:
    - Removing backslashes.
    - Adding 'https://' if missing.
    - Truncating after common domain endings.
    """
    url = url.replace('\\', '')

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    valid_url_pattern = re.compile(r'(https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')

    match = valid_url_pattern.match(url)
    if match:
        return match.group(0)
    
    return url

def clean_urls(urls):
    """
    This function cleans up invalid URLs by fixing malformed entries
    and removing duplicates.
    """
    cleaned_urls = []
    
    for url in urls:
        fixed_url = fix_malformed_url(url)
        
        if fixed_url not in cleaned_urls:
            cleaned_urls.append(fixed_url)
    
    return cleaned_urls

def extract_urls(text):
    """
    This function takes a block of text and returns a list of all URLs found using regular expressions.
    """
    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
    
    urls = set(re.findall(url_pattern, text))
    
    return list(urls)

    
def scrape_google_search(query, location, start=0):
    """
    This function takes a query and a location, formats them for a Google Search URL,
    sends the request, and returns the HTML content of the search results.
    """
    query = query.strip().replace(' ', '+')
    location = location.strip().replace(' ', '+')

    url = f'https://www.google.com/search?q={query}+{location}&start={start}'

    # Randomize User-Agent for each request
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Referer': 'https://www.google.com/'  # Add referer header to simulate a search engine result
    }

    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.text
        elif response.status_code == 403:
            logging.warning(f"Error 403: Forbidden - Access denied for {url}")
        else:
            logging.warning(f"Failed to retrieve the page. Status code: {response.status_code}")
            
    except Exception as e:
        logging.error(f"An error occurred while scraping Google: {e}")

    return None


if __name__ == "__main__":

    all_results = ""
    for i in range(0, 100, 10):  # Increment by 10 to scrape pages correctly
        logging.info(f"Scraping results for start={i}")
        result = scrape_google_search(query="dentists", location="los angeles", start=i)
        
        if result:
            all_results += result
        else:
            logging.warning(f"Failed to retrieve results for start={i}")

        # Random sleep between 2 and 5 seconds to avoid rate limiting
        sleep_time = random.uniform(2, 5)
        logging.info(f"Sleeping for {sleep_time:.2f} seconds")
        time.sleep(sleep_time)
    
    logging.debug(all_results)
    logging.info(f"Number of results scraped: {len(all_results)}")

    # Extract URLs from the HTML response
    result_urls = extract_urls(all_results)
    logging.debug(result_urls)
    logging.info(f"Number of URLs extracted: {len(result_urls)}")
    
    # Clean the URLs
    cleaned_urls = clean_urls(result_urls)

    # Filter out unwanted URLs
    exclude_terms = ['google', 'gstatic']
    filtered_urls = filter_urls(cleaned_urls, exclude_terms)
    logging.info(f"Number of filtered URLs: {len(filtered_urls)}")
    logging.debug(filtered_urls)

    # Extract emails from the URLs
    emails = process_urls_for_emails(filtered_urls)
    logging.info(f"Number of URLs scraped for emails: {len(emails)}")
    logging.info(emails)


    # Convert the dictionary to a list of tuples, and join list values (emails) into strings
    data_tuples = [(url, ', '.join(emails) if isinstance(emails, list) else emails) for url, emails in emails.items()]

    # Create a DataFrame from the list of tuples
    df = pd.DataFrame(data_tuples, columns=['URL', 'Emails'])

    # Save the DataFrame to a CSV file
    csv_file = "urls_and_emails_pandas.csv"
    df.to_csv(csv_file, index=False)

    print(f"Data has been saved to {csv_file}")