from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import html2text
import PyPDF2
import io
import re
from typing import Optional, List
import uvicorn
import boto3
import json
import os
from dotenv import load_dotenv
from datetime import datetime

from database import connect_to_mongo, close_mongo_connection, get_optimizations_collection, get_users_collection
from models import ResumeOptimization, User

load_dotenv()

app = FastAPI(title="Resume Optimizer API")

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class JobPostingRequest(BaseModel):
    url: HttpUrl
    resume_text: Optional[str] = None

class ResumeResponse(BaseModel):
    id: str
    optimized_resume: str
    suggestions: list[str]
    match_score: float
    created_at: datetime
    job_posting_content: str

async def scrape_with_playwright(url: str) -> str:
    """Use Playwright for JavaScript-heavy sites"""
    print("Using Playwright for JavaScript rendering...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Navigate to the page with a longer timeout
            await page.goto(url, wait_until='networkidle', timeout=60000)
            
            # Wait for content to load
            await page.wait_for_timeout(3000)
            
            # Get the full page content
            content = await page.content()
            
            # Convert to text using html2text for better formatting
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.ignore_emphasis = True
            h.body_width = 0
            
            text = h.handle(content)
            
            # Clean up the text
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = ' '.join(lines)
            
            return text
            
        finally:
            await browser.close()

async def cleanse_job_posting_with_llm(raw_text: str) -> str:
    """Use LLM to extract only relevant job posting content"""
    
    # Check if AWS credentials are available
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    
    try:
        # Initialize Bedrock client
        bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name=aws_region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
    except Exception as e:
        # Return original text if no AWS credentials
        return raw_text[:5000]
    
    prompt = f"""Extract only the relevant job posting information from the following webpage content. 
    Remove all boilerplate text such as:
    - Company policies about equal opportunity employment
    - Disability/accessibility statements
    - Cookie policies
    - Navigation menus
    - Footer information
    - Legal disclaimers
    - Generic company marketing text
    
    Keep only:
    - Job title
    - Job description
    - Required qualifications and skills
    - Responsibilities
    - Nice-to-have skills
    - Salary/benefits information (if present)
    - Location
    - Job type (full-time, contract, etc.)
    
    Raw webpage content:
    {raw_text[:8000]}
    
    Return only the cleaned job posting content, nothing else."""
    
    try:
        # Prepare the request for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1
        }
        
        # Invoke Claude model
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        cleaned_text = response_body['content'][0]['text']
        
        print(f"LLM cleaned text from {len(raw_text)} to {len(cleaned_text)} characters")
        return cleaned_text
        
    except Exception as e:
        print(f"Error cleansing with LLM: {e}")
        # Fallback to simple truncation
        return raw_text[:5000]

async def scrape_job_posting(url: str) -> tuple[str, str]:
    """Scrape and extract text from job posting webpage
    Returns: (cleansed_content, raw_content)
    """
    print(f"Scraping URL: {url}")
    
    # First try simple HTTP request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    raw_text = ""
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, follow_redirects=True, timeout=30.0)
            response.raise_for_status()
            print(f"Response status: {response.status_code}")
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        
        # Get text
        text = soup.get_text()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = ' '.join(lines)
        
        # If we got reasonable amount of text, cleanse and return it
        if len(text) > 500:
            print(f"Successfully scraped {len(text)} characters with simple HTTP")
            raw_text = text
            cleansed_text = await cleanse_job_posting_with_llm(text)
            return cleansed_text, raw_text
            
        # Otherwise, try Playwright
        print(f"Simple scrape only got {len(text)} chars, trying Playwright...")
        text = await scrape_with_playwright(url)
        
        if len(text) > 100:
            print(f"Successfully scraped {len(text)} characters with Playwright")
            raw_text = text
            cleansed_text = await cleanse_job_posting_with_llm(text)
            return cleansed_text, raw_text
        else:
            error_msg = "Unable to extract job posting content. The page might be protected or require manual access."
            return error_msg, error_msg
            
    except Exception as e:
        print(f"Error scraping: {e}")
        # Try Playwright as fallback
        try:
            text = await scrape_with_playwright(url)
            if len(text) > 100:
                raw_text = text
                cleansed_text = await cleanse_job_posting_with_llm(text)
                return cleansed_text, raw_text
        except Exception as e2:
            print(f"Playwright also failed: {e2}")
        
        error_msg = f"Unable to scrape job posting. Error: {str(e)}"
        return error_msg, error_msg

def parse_pdf_resume(file_content: bytes) -> str:
    """Extract text from PDF resume"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing PDF: {str(e)}")

def parse_text_resume(content: str) -> str:
    """Clean and parse text resume"""
    # Basic cleaning
    content = re.sub(r'\s+', ' ', content)
    return content.strip()

async def optimize_resume_with_llm(job_posting: str, resume: str) -> dict:
    """Use AWS Bedrock Claude API to optimize resume based on job posting"""
    
    # Check if AWS credentials are available
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    
    try:
        # Initialize Bedrock client
        bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name=aws_region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
    except Exception as e:
        # Return a basic optimization if no AWS credentials
        return {
            "optimized_resume": resume,
            "suggestions": [
                "Add AWS credentials to .env file for AI-powered optimization",
                "Review job requirements and align your skills",
                "Highlight relevant experience",
                "Use keywords from the job posting"
            ],
            "match_score": 0.5
        }
    
    prompt = f"""You are an expert resume writer. Given a job posting and a current resume, 
    create an optimized version of the resume that:
    1. Highlights skills and experiences most relevant to the job
    2. Uses keywords from the job posting appropriately
    3. Maintains truthfulness - only reorganize and emphasize existing content
    4. Follows best resume practices
    
    Job Posting:
    {job_posting[:3000]}  # Limit to avoid token limits
    
    Current Resume:
    {resume[:3000]}  # Limit to avoid token limits
    
    Provide the response in JSON format with exactly these fields:
    - "optimized_resume": The improved resume text
    - "suggestions": List of specific improvements made
    - "match_score": A score from 0-1 indicating how well the resume matches the job
    
    Return only valid JSON, no additional text."""
    
    try:
        # Prepare the request for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7
        }
        
        # Invoke Claude model
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        claude_response = response_body['content'][0]['text']
        
        # Extract JSON from Claude's response
        # Claude might wrap JSON in markdown code blocks
        import re
        json_match = re.search(r'\{[\s\S]*\}', claude_response)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(claude_response)
        
        return result
        
    except json.JSONDecodeError as e:
        # Handle JSON parsing errors
        return {
            "optimized_resume": resume,
            "suggestions": [
                "AI response parsing error",
                "Please review job requirements manually",
                "Consider adding keywords from the job posting",
                f"JSON Error: {str(e)}"
            ],
            "match_score": 0.5
        }
    except Exception as e:
        # Fallback for API errors
        return {
            "optimized_resume": resume,
            "suggestions": [
                "Could not connect to AWS Bedrock service",
                "Please check AWS credentials and permissions",
                "Ensure you have access to Claude model in Bedrock",
                f"Error: {str(e)}"
            ],
            "match_score": 0.5
        }

@app.get("/")
async def root():
    return {"message": "Resume Optimizer API", "endpoints": ["/optimize", "/docs", "/api/optimizations", "/api/optimizations/{id}"]}

@app.post("/optimize", response_model=ResumeResponse)
async def optimize_resume(
    job_url: str = Form(...),
    resume_file: Optional[UploadFile] = File(None),
    resume_text: Optional[str] = Form(None)
):
    """
    Optimize a resume based on a job posting.
    
    Either upload a PDF resume file or provide resume text directly.
    """
    
    # Validate input
    if not resume_file and not resume_text:
        raise HTTPException(
            status_code=400, 
            detail="Either resume_file or resume_text must be provided"
        )
    
    # Scrape job posting
    job_posting_cleansed, job_posting_raw = await scrape_job_posting(job_url)
    print(f"Scraped job posting - Raw: {len(job_posting_raw)} chars, Cleansed: {len(job_posting_cleansed)} chars")
    print(f"First 200 chars of cleansed: {job_posting_cleansed[:200]}")
    
    # Parse resume
    if resume_file:
        content = await resume_file.read()
        if resume_file.filename.lower().endswith('.pdf'):
            resume_content = parse_pdf_resume(content)
        else:
            resume_content = parse_text_resume(content.decode('utf-8'))
    else:
        resume_content = parse_text_resume(resume_text)
    
    # Optimize resume using cleansed content
    optimization_result = await optimize_resume_with_llm(job_posting_cleansed, resume_content)
    
    # Save to database
    optimization_doc = ResumeOptimization(
        user_email="anonymous@example.com",  # TODO: Add user authentication
        job_url=job_url,
        job_posting_content=job_posting_cleansed,
        job_posting_raw=job_posting_raw,
        original_resume=resume_content,
        optimized_resume=optimization_result["optimized_resume"],
        suggestions=optimization_result["suggestions"],
        match_score=optimization_result["match_score"]
    )
    
    collection = get_optimizations_collection()
    doc_dict = optimization_doc.model_dump(by_alias=True, exclude={'id'})
    result = await collection.insert_one(doc_dict)
    optimization_doc.id = str(result.inserted_id)
    
    response = ResumeResponse(
        id=str(optimization_doc.id),
        optimized_resume=optimization_result["optimized_resume"],
        suggestions=optimization_result["suggestions"],
        match_score=optimization_result["match_score"],
        created_at=optimization_doc.created_at,
        job_posting_content=job_posting_cleansed
    )
    print(f"Returning job_posting_content in response: {len(response.job_posting_content)} chars")
    return response

@app.post("/optimize-json", response_model=ResumeResponse)
async def optimize_resume_json(request: JobPostingRequest):
    """
    Alternative endpoint that accepts JSON input.
    """
    job_posting_cleansed, job_posting_raw = await scrape_job_posting(str(request.url))
    
    if not request.resume_text:
        raise HTTPException(
            status_code=400,
            detail="resume_text must be provided in JSON request"
        )
    
    resume_content = parse_text_resume(request.resume_text)
    optimization_result = await optimize_resume_with_llm(job_posting_cleansed, resume_content)
    
    # Save to database
    optimization_doc = ResumeOptimization(
        user_email="anonymous@example.com",  # TODO: Add user authentication
        job_url=str(request.url),
        job_posting_content=job_posting_cleansed,
        job_posting_raw=job_posting_raw,
        original_resume=resume_content,
        optimized_resume=optimization_result["optimized_resume"],
        suggestions=optimization_result["suggestions"],
        match_score=optimization_result["match_score"]
    )
    
    collection = get_optimizations_collection()
    doc_dict = optimization_doc.model_dump(by_alias=True, exclude={'id'})
    result = await collection.insert_one(doc_dict)
    optimization_doc.id = str(result.inserted_id)
    
    response = ResumeResponse(
        id=str(optimization_doc.id),
        optimized_resume=optimization_result["optimized_resume"],
        suggestions=optimization_result["suggestions"],
        match_score=optimization_result["match_score"],
        created_at=optimization_doc.created_at,
        job_posting_content=job_posting_cleansed
    )
    print(f"Returning job_posting_content in response: {len(response.job_posting_content)} chars")
    return response

@app.get("/api/optimizations", response_model=List[ResumeOptimization])
async def get_optimizations(skip: int = 0, limit: int = 10):
    """Get list of resume optimizations"""
    collection = get_optimizations_collection()
    cursor = collection.find().skip(skip).limit(limit).sort("created_at", -1)
    optimizations = await cursor.to_list(length=limit)
    return optimizations

@app.get("/api/optimizations/{optimization_id}", response_model=ResumeOptimization)
async def get_optimization(optimization_id: str):
    """Get a specific optimization by ID"""
    from bson import ObjectId
    
    if not ObjectId.is_valid(optimization_id):
        raise HTTPException(status_code=400, detail="Invalid optimization ID")
    
    collection = get_optimizations_collection()
    optimization = await collection.find_one({"_id": ObjectId(optimization_id)})
    
    if not optimization:
        raise HTTPException(status_code=404, detail="Optimization not found")
    
    return optimization

@app.delete("/api/optimizations/{optimization_id}")
async def delete_optimization(optimization_id: str):
    """Delete a specific optimization"""
    from bson import ObjectId
    
    if not ObjectId.is_valid(optimization_id):
        raise HTTPException(status_code=400, detail="Invalid optimization ID")
    
    collection = get_optimizations_collection()
    result = await collection.delete_one({"_id": ObjectId(optimization_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Optimization not found")
    
    return {"message": "Optimization deleted successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)