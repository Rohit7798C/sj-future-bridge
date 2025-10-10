from pydantic import BaseModel,EmailStr,Field
from typing import Optional, Union 
from enum import Enum
from datetime import datetime
class ExamType(str, Enum):
    BCA_MCA_Int = 'BCA_MCA_Int'
    BBA_BMS_BBM_MBA_Int = 'BBA_BMS_BBM_MBA_Int'
    B_and_D_Pharmacy = 'B_and_D_Pharmacy'

class questionSchema(BaseModel):
    question: dict

class UsernameSchema(BaseModel):
    username: EmailStr

class EmailSchema(BaseModel):
    email: EmailStr

class TriggerStandardSchema(BaseModel):
    email: EmailStr
    coupon: Optional[dict] = None
class paymentOrderIdSchema(BaseModel):
    order_id: str


class ResponseSchema(BaseModel):
    message: Optional[str] = None
    success: bool = False
    data: Union[dict, str, list] = {}


class PremiumCouponResponseSchema(BaseModel):
    message: Optional[str] = None
    success: bool = True
    coupons: Optional[dict] = None

class GetQuestionsetByVersionSchema(BaseModel):
    version: Optional[int] = 1

class ValidateOtpBody(BaseModel):
    email : EmailStr
    user_type : Optional[str] = 'user'
    otp : int = Field(gt=100000, lt=999999)
class ValidateOtpResponse(BaseModel):
    isValidOtp: bool
    accessToken: Optional[str] = None
    name: Optional[str] = None
    profileIcon: Optional[str] = None

class CollegeConfigurationRequest(BaseModel):
    exam_type: ExamType = ExamType.BCA_MCA_Int
    score: float = Field(..., description="Score")
    district: str = Field(..., description="District")
    gender: str = Field(..., description="Gender")
    tenth_percentage: float = Field(..., description="10th Percentage")
    twelth_percentage: float = Field(..., description="12th or Equivalent Percentage")
    category: str = Field(..., description="Category")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the configuration")


class RoundPreferencesRequest(BaseModel):
    exam_type: ExamType = ExamType.BCA_MCA_Int
    branches: list = Field(..., description="Branches")
    locations: list = Field(..., description="Locations")
    district: str = Field(..., description="District")
    gender: str = Field(..., description="Gender")
    round_no: int = Field(default=1, description="Round Number")
    category: str = Field(..., description="Category")
    score: float = Field(..., description="Score")
    last_college_round_choice_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the preferences")

class CollegeRoundPrefrence(BaseModel):
    college_name: str = Field(..., description="College Name")
    college_code: str = Field(..., description="College Code")
    course_code: str = Field(..., description="Course Code")
    course_name: str = Field(..., description="Course Name")
    exam_type: ExamType = ExamType.BCA_MCA_Int
    round_no: int = Field(default=1, description="Round Number")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the preferences")


