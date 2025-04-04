"""
FastAPI application for LeadGenPro
"""
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, validator

from leadgenpro.scraper import (
    scrape_and_process,
    sanitize_string,
)

# Create data directory if not exists
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

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
    job_id = f"{sanitize_string(request.query)}_{sanitize_string(request.location)}_{int(__import__('time').time())}"
    
    # Initialize job
    scrape_jobs[job_id] = {
        "status": "queued",
        "query": request.query,
        "location": request.location,
        "results": request.results,
        "created_at": __import__('time').time()
    }
    
    # Add task to background
    background_tasks.add_task(
        scrape_and_process,
        job_id=job_id,
        query=request.query,
        location=request.location,
        results=request.results,
        jobs_dict=scrape_jobs
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