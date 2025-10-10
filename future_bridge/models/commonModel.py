from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class OTPValidator(BaseModel):
    """
    Represents an OTP Validator with email, OTP, and verification status.
    """
    useremail: EmailStr
    otp: int = Field(gt=100000, lt=999999)
    verified: Optional[bool] = False


class CollegeConfigurationRequest(BaseModel):
    """
    Represents a College Configuration Request with user email, exam type, score, tenth percentage, twelth percentage, and category.
    """
    useremail: EmailStr
    exam_type: str
    score: float = Field(..., description="Score")
    district: str = Field(..., description="District")
    gender: str = Field(..., description="Gender")
    tenth_percentage: float = Field(..., description="10th Percentage")
    twelth_percentage: float = Field(..., description="12th or Equivalent Percentage")
    category: str = Field(..., description="Category")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the configuration")

class RoundPreferencesRequest(BaseModel):
    """
    Represents a Round Preferences Request with user email, round number, and preferences.
    """
    useremail: EmailStr = Field(..., description="User Email")
    exam_type: str = Field(..., description="Exam Type")
    round_no: int = Field(..., description="Round Number")
    branches: list = Field(..., description="Branches")
    locations: list = Field(..., description="Locations")
    round_no: int = Field(default=1, description="Round Number")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the preferences")


class CollegeRoundPrefrence(BaseModel):
    """
    Represents a College Round Preference with user email, exam type, round number, college name, college code, course code, course name, city, state, and timestamp.
    """
    useremail: EmailStr = Field(..., description="User Email")
    exam_type: str = Field(..., description="Exam Type")
    round_no: int = Field(..., description="Round Number")
    college_name: str = Field(..., description="College Name")
    college_code: str = Field(..., description="College Code")
    course_code: str = Field(..., description="Course Code")
    course_name: str = Field(..., description="Course Name")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the preferences")
