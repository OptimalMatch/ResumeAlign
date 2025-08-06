from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from bson import ObjectId

class ResumeOptimization(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[str] = Field(default=None, alias="_id")
    user_email: str
    job_url: str
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    job_posting_content: str  # Cleansed content
    job_posting_raw: Optional[str] = None  # Raw scraped content before cleansing
    original_resume: str
    optimized_resume: str
    suggestions: List[str]
    match_score: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class User(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[str] = Field(default=None, alias="_id")
    email: str
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    optimization_count: int = 0