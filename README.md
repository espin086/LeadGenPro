# LeadGenPro

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/python-3.8%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-modern-brightgreen.svg" alt="FastAPI">
</p>

A professional lead generation tool that automates the discovery of business contact information by scraping Google search results and extracting emails, phone numbers, and relevant content from websites.

## 🚀 Features

- **Automated Lead Discovery**: Search for businesses based on type and location
- **Contact Information Extraction**: Automatically find emails and phone numbers
- **Asynchronous Processing**: Background job processing for better user experience
- **RESTful API**: Well-documented API endpoints with Swagger UI
- **Data Export**: Download results as CSV files
- **Robust Error Handling**: Graceful handling of network errors and rate limiting

## 📋 Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Examples](#examples)
- [Ethical Use & Compliance](#ethical-use--compliance)
- [License](#license)

## 🔧 Installation

### Prerequisites

- Python 3.8 or higher
- [Poetry](https://python-poetry.org/) for dependency management

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/LeadGenPro.git
   cd LeadGenPro
   ```

2. Install dependencies with Poetry:
   ```bash
   poetry install
   ```

3. Run the application:
   ```bash
   poetry run python -m leadgenpro
   ```

   The API will be available at `http://localhost:8000`.

## 🔍 Usage

LeadGenPro provides two main ways to use the application:

### Via Web Interface (Swagger UI)

1. Start the application
2. Open `http://localhost:8000/docs` in your browser
3. Use the interactive Swagger UI to make API calls

### Via API Calls

Use any HTTP client (curl, Postman, or code) to access the API endpoints:

```bash
# Start a scraping job
curl -X POST "http://localhost:8000/scrape" \
     -H "Content-Type: application/json" \
     -d '{"query": "plumbers", "location": "boston", "results": 20}'

# Check job status
curl -X GET "http://localhost:8000/jobs/plumbers_boston_1234567890"

# Download results
curl -X GET "http://localhost:8000/download/plumbers_boston_1234567890" --output results.csv
```

## 📚 API Documentation

### Health Check

```
GET /
```

Returns a simple status message to confirm the API is running.

### Start a Scraping Job

```
POST /scrape
```

**Parameters**:
- `query` (string): The type of business to search for (e.g., "plumbers", "dentists")
- `location` (string): The location to search in (e.g., "boston", "los angeles")
- `results` (integer): Number of results to process (must be a multiple of 10, max 100)

**Response**: A job ID and status information

### Check Job Status

```
GET /jobs/{job_id}
```

**Parameters**:
- `job_id` (path parameter): The ID of the job to check

**Response**: Status of the job and results if completed

### List All Jobs

```
GET /jobs
```

**Parameters**:
- `status` (query parameter, optional): Filter by job status ("queued", "processing", "completed", "failed")

**Response**: List of jobs with their statuses

### Download Results

```
GET /download/{job_id}
```

**Parameters**:
- `job_id` (path parameter): The ID of the completed job

**Response**: CSV file with the lead information

## 💡 Examples

### Finding Plumbers in Boston

```python
import requests

# Start a scraping job
response = requests.post(
    "http://localhost:8000/scrape",
    json={"query": "plumbers", "location": "boston", "results": 20}
)
job_id = response.json()["job_id"]
print(f"Started job: {job_id}")

# Check status periodically
import time
while True:
    response = requests.get(f"http://localhost:8000/jobs/{job_id}")
    status = response.json()["status"]
    print(f"Job status: {status}")
    
    if status in ["completed", "failed"]:
        break
        
    time.sleep(5)  # Wait 5 seconds before checking again

# Download results if job completed successfully
if status == "completed":
    response = requests.get(f"http://localhost:8000/download/{job_id}")
    with open("plumbers_boston.csv", "wb") as f:
        f.write(response.content)
    print("Results downloaded to plumbers_boston.csv")
```

## ⚖️ Ethical Use & Compliance

When using LeadGenPro, please keep the following guidelines in mind:

- **Respect Robots.txt**: The tool attempts to respect website rules, but you should review target sites' robots.txt files
- **Rate Limiting**: The tool implements delays between requests to avoid overloading websites
- **Data Privacy Laws**: Ensure compliance with GDPR, CCPA, and other relevant data protection regulations when storing and using the collected information
- **Terms of Service**: Using this tool may violate the terms of service of some websites, including search engines
- **Educational Purpose**: This tool is provided primarily for educational purposes

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

If you encounter any issues or have questions, please open an issue on GitHub.
