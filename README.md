# Resume Optimizer

A full-stack application that optimizes resumes based on job postings using AWS Bedrock with Claude AI.

## Features

- **AI-Powered Optimization**: Uses AWS Bedrock with Claude model to analyze job postings and optimize resumes
- **Multiple Input Methods**: Support for PDF upload, text file upload, or direct text input
- **Smart Suggestions**: Provides specific recommendations for improving resume match
- **Match Score**: Calculates how well your resume matches the job requirements
- **History Tracking**: Stores optimization history in MongoDB
- **Modern UI**: Clean, responsive React interface with Material-UI
- **Containerized**: Fully dockerized for easy deployment

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: React with TypeScript and Material-UI
- **Database**: MongoDB
- **AI**: AWS Bedrock with Claude 3 Sonnet
- **Containerization**: Docker & Docker Compose

## Prerequisites

- Docker and Docker Compose installed
- AWS Account with Bedrock access
- AWS credentials with permissions for Bedrock

## Setup

1. Clone the repository

2. Configure AWS credentials:
   ```bash
   cd backend
   cp .env.example .env
   ```
   Edit `.env` and add your AWS credentials:
   ```
   AWS_ACCESS_KEY_ID=your_key_id
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_REGION=us-east-1
   ```

3. Run with Docker Compose:
   ```bash
   docker-compose up -d
   ```

4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8001
   - API Documentation: http://localhost:8001/docs
   - MongoDB: localhost:27019 (external access)

## Usage

1. Navigate to http://localhost:3000
2. Enter a job posting URL
3. Upload your resume (PDF/TXT) or paste the text
4. Click "Optimize Resume"
5. Review the optimized resume and suggestions
6. Download the optimized version

## API Endpoints

- `POST /optimize` - Optimize resume with file upload
- `POST /optimize-json` - Optimize resume with JSON payload
- `GET /api/optimizations` - Get optimization history
- `GET /api/optimizations/{id}` - Get specific optimization
- `DELETE /api/optimizations/{id}` - Delete optimization

## Development

### Backend Development
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend Development
```bash
cd frontend
npm install
npm start
```

## AWS Bedrock Requirements

1. Enable Amazon Bedrock in your AWS account
2. Request access to Claude 3 Sonnet model
3. Ensure your IAM user has the `bedrock:InvokeModel` permission
4. The model must be available in your selected region

## Architecture

- **Frontend**: React app served by Nginx, proxies API requests to backend
- **Backend**: FastAPI application handling resume optimization and data persistence
- **Database**: MongoDB for storing optimization history
- **AI Integration**: AWS Bedrock API for Claude model inference

## Security Notes

- Never commit `.env` files with real credentials
- Use IAM roles in production instead of access keys
- Configure CORS appropriately for production
- Add authentication for production use