"""
Entry point for running the LeadGenPro API
"""
import uvicorn

def main():
    """Run the FastAPI application using Uvicorn."""
    uvicorn.run("leadgenpro.api:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main() 