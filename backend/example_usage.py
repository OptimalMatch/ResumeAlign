import httpx
import asyncio

# Note: This application uses AWS Bedrock with Claude model for AI optimization
# Make sure you have AWS credentials configured in your .env file

# Example 1: Using form data with file upload
async def example_with_file():
    async with httpx.AsyncClient() as client:
        with open("example_resume.pdf", "rb") as f:
            files = {"resume_file": ("resume.pdf", f, "application/pdf")}
            data = {"job_url": "https://example.com/job-posting"}
            
            response = await client.post(
                "http://localhost:8000/optimize",
                files=files,
                data=data
            )
            
            print(response.json())

# Example 2: Using form data with text
async def example_with_text():
    async with httpx.AsyncClient() as client:
        data = {
            "job_url": "https://example.com/job-posting",
            "resume_text": """
            John Doe
            Software Engineer
            
            Experience:
            - 5 years Python development
            - FastAPI, Django experience
            - AWS deployment
            
            Education:
            BS Computer Science
            """
        }
        
        response = await client.post(
            "http://localhost:8000/optimize",
            data=data
        )
        
        print(response.json())

# Example 3: Using JSON endpoint
async def example_with_json():
    async with httpx.AsyncClient() as client:
        json_data = {
            "url": "https://example.com/job-posting",
            "resume_text": "Your resume content here..."
        }
        
        response = await client.post(
            "http://localhost:8000/optimize-json",
            json=json_data
        )
        
        result = response.json()
        print(f"Match Score: {result['match_score']}")
        print(f"Suggestions: {result['suggestions']}")
        print(f"Optimized Resume:\n{result['optimized_resume']}")

# Example using curl
"""
# With file upload:
curl -X POST "http://localhost:8000/optimize" \
  -F "job_url=https://example.com/job-posting" \
  -F "resume_file=@resume.pdf"

# With text:
curl -X POST "http://localhost:8000/optimize" \
  -F "job_url=https://example.com/job-posting" \
  -F "resume_text=Your resume content here"

# With JSON:
curl -X POST "http://localhost:8000/optimize-json" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/job-posting",
    "resume_text": "Your resume content here"
  }'
"""

if __name__ == "__main__":
    # Run example
    asyncio.run(example_with_text())