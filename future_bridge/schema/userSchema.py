from bson import timestamp
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime

class UserRequest(BaseModel):
    """
    Request model for storing user data
    """
    username: EmailStr
    name: Optional[str] = ""
    profileIcon: Optional[str] = ""
    user_level: str = 'Standard'  # Default level set to "Standard"
    questionnaire: Optional[list] = None
    resume: Optional[list] = []
    answers: Optional[dict] = {}
    mobile: Optional[int] = Field(None, gt=1000000000, lt=9999999999)
    user_origin: str = "Future Bridge"


class FeedBack(BaseModel):
    """
    Request model for storing user data
    """
    username: EmailStr
    feedback: Optional[str] = ""
    rating: Optional[int] = Field(None, gt=0, lt=6)


class CollegeDetails(BaseModel):
    """
    Request model for storing user data
    """
    username: EmailStr
    college_name: str = Field(..., description="Name of the college")
    college_code: int = Field(..., description="Code of the college")
    course_name: str = Field(..., description="Name of the course")
    course_code: int = Field(..., description="Code of the course")
    choice_code: int = Field(..., description="Code of the choice")
    round: int = Field(..., description="Round of the college")
    timestamp: datetime = datetime.now()

class RoundPreferences(BaseModel):
    """
    Request model for storing user data
    """
    round: int = Field(..., description="Round of the college")
    branches: list[str] = Field(..., description="List of branches")
    cities: list[str] = Field(..., description="List of cities")
    timestamp: datetime = datetime.now()
class UserResponse(BaseModel):
    """
    Response model for user operations
    """
    message: str
    success: bool
    data: Dict[str, Any] 