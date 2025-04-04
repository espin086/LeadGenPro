import re
import time
import random
import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

import requests
import pandas as pd
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, HttpUrl, validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("leadgenpro")

# Create FastAPI app
app = FastAPI(
    title="LeadGenPro",
    description="A professional Lead Generation Tool that extracts contact information from websites",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Pydantic Models
class ScrapeRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query term")
    location: str = Field(..., min_length=1, description="Location to search for")
    results: int = Field(..., ge=10, le=100, description="Number of results to scrape (must be a multiple of 10)")
    
    @validator('results')
    def validate_results(cls, v):
        if v % 10 != 0:
            raise ValueError('Results must be a multiple of 10')
        return v

class ContactInfo(BaseModel):
    url: str
    emails: List[str] = []
    phone_numbers: List[str] = []
    all_text: Optional[str] = None

class ScrapeResponse(BaseModel):
    job_id: str
    status: str
    message: str

class ScrapeResult(BaseModel):
    query: str
    location: str
    results: int
    contact_info: List[ContactInfo]
    file_path: Optional[str] = None

# In-memory job storage (replace with a database in production)
scrape_jobs: Dict[str, Dict[str, Any]] = {}

# Service Functions
def scrape_google_search(query: str, location: str, start: int = 0) -> Optional[str]:
    """
    Scrape Google search results for a given query and location.
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
            logger.warning(f"Error 403: Forbidden - Access denied for {url}")
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
    
    for url in urls:
        sleep_delay = random.uniform(2, 4)
        logger.info(f"Sleeping for {sleep_delay:.2f} seconds")
        time.sleep(sleep_delay)  # Sleep for 2-4 seconds to avoid rate limiting
        
        logger.info(f"Processing URL: {url}")
        
        content = get_page_content(url)
        
        if content:
            emails = extract_emails_from_content(content)
            phone_numbers = extract_phone_numbers_from_content(content)
            all_text = extract_all_text(content)
            
            results.append(ContactInfo(
                url=url,
                emails=emails,
                phone_numbers=phone_numbers,
                all_text=all_text
            ))
    
    return results

def extract_urls(text: str) -> List[str]:
    """Extract URLs from text."""
    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
    urls = set(re.findall(url_pattern, text))
    return list(urls)

def clean_urls(urls: List[str]) -> List[str]:
    """Clean and deduplicate URLs."""
    cleaned_urls = []
    for url in urls:
        fixed_url = fix_malformed_url(url)
        if fixed_url not in cleaned_urls:
            cleaned_urls.append(fixed_url)
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
    filtered_urls = [url for url in urls if not any(term in url for term in exclude_terms)]
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
    results: int
) -> None:
    """
    Background task to scrape Google and process the results.
    """
    try:
        # Update job status
        scrape_jobs[job_id]["status"] = "processing"
        
        all_results = ""
        
        # Scrape Google search results
        for i in range(0, results, 10):
            logger.info(f"Scraping results for start={i}")
            result = scrape_google_search(query=query, location=location, start=i)
            
            if result:
                all_results += result
            else:
                logger.warning(f"Failed to retrieve results for start={i}")

            sleep_time = random.uniform(2, 5)
            logger.info(f"Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        # Extract and process URLs
        result_urls = extract_urls(all_results)
        logger.info(f"Number of URLs extracted: {len(result_urls)}")
        
        cleaned_urls = clean_urls(result_urls)
        exclude_terms = ['google', 'gstatic', 'usnews']
        filtered_urls = filter_urls(cleaned_urls, exclude_terms)
        logger.info(f"Number of filtered URLs: {len(filtered_urls)}")

        # Process URLs to extract contact information
        contact_info = process_urls_for_contact_info(filtered_urls)
        logger.info(f"Number of URLs processed for contact info: {len(contact_info)}")

        # Save results to CSV
        file_path = save_to_csv(contact_info, query, location)
        
        # Update job with results
        scrape_jobs[job_id].update({
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
        scrape_jobs[job_id].update({
            "status": "failed",
            "error": str(e)
        })

# API Endpoints
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "message": "LeadGenPro API is running"}

@app.post("/scrape", response_model=ScrapeResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Scraping"])
async def scrape_leads(
    background_tasks: BackgroundTasks,
    request: ScrapeRequest
):
    """
    Start a scraping job to extract contact information based on search query and location.
    
    This is an asynchronous operation that will return immediately with a job ID.
    You can check the status of the job using the /jobs/{job_id} endpoint.
    """
    job_id = f"{sanitize_string(request.query)}_{sanitize_string(request.location)}_{int(time.time())}"
    
    # Initialize job
    scrape_jobs[job_id] = {
        "status": "queued",
        "query": request.query,
        "location": request.location,
        "results": request.results,
        "created_at": time.time()
    }
    
    # Add task to background
    background_tasks.add_task(
        scrape_and_process,
        job_id=job_id,
        query=request.query,
        location=request.location,
        results=request.results
    )
    
    return ScrapeResponse(
        job_id=job_id,
        status="queued",
        message="Scraping job has been queued and will be processed in the background"
    )

@app.get("/jobs/{job_id}", tags=["Jobs"])
async def get_job_status(job_id: str):
    """Get the status of a scraping job."""
    if job_id not in scrape_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = scrape_jobs[job_id]
    
    response = {
        "job_id": job_id,
        "status": job["status"],
        "query": job["query"],
        "location": job["location"],
        "created_at": job["created_at"]
    }
    
    if job["status"] == "completed":
        response["result"] = job["result"]
    elif job["status"] == "failed":
        response["error"] = job["error"]
    
    return response

@app.get("/download/{job_id}", tags=["Download"])
async def download_results(job_id: str):
    """Download the CSV file for a completed job."""
    if job_id not in scrape_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = scrape_jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Job {job_id} is not completed. Current status: {job['status']}"
        )
    
    file_path = job["result"].file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"CSV file not found")
    
    return FileResponse(
        path=file_path, 
        filename=os.path.basename(file_path),
        media_type="text/csv"
    )

@app.get("/jobs", tags=["Jobs"])
async def list_jobs(
    status: Optional[str] = Query(None, enum=["queued", "processing", "completed", "failed"])
):
    """List all jobs, optionally filtered by status."""
    if not scrape_jobs:
        return {"jobs": []}
    
    jobs = []
    for job_id, job in scrape_jobs.items():
        if status is None or job["status"] == status:
            jobs.append({
                "job_id": job_id,
                "status": job["status"],
                "query": job["query"],
                "location": job["location"],
                "created_at": job["created_at"]
            })
    
    return {"jobs": jobs}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("scraper:app", host="0.0.0.0", port=8000, reload=True)