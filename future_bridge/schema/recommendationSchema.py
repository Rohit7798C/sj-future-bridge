from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field

class OtherEntranceExam(BaseModel):
    examName: Optional[str] = None
    percentileOrScore: Optional[float] = None

class ExamPercentiles(BaseModel):
    CET: Optional[float] = None
    JEE: Optional[float] = None
    otherEntranceExam: Optional[List[OtherEntranceExam]] = None

class AcademicMarks(BaseModel):
    tenthGradeMarksPercent: float = Field(..., alias="_10thGradeMarksPercent")
    twelfthGradeMarksPercent: float = Field(..., alias="_12thGradeMarksPercent")
    groupingMarksPercent: float

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True
        orm_mode = True

class EducationBackground(BaseModel):
    educationType: str
    stream: str

class AchievementsExperience(BaseModel):
    sportsAchievements: Optional[str] = None
    certifications: Optional[str] = None
    internshipsWorkExperience: Optional[str] = None
    otherAchievements: Optional[str] = None

class Preferences(BaseModel):
    engineeringBranches: List[str]
    preferredCities: List[str]

class CampusFacilitiesEnvironment(BaseModel):
    hostelFacility: Optional[str] = None
    campusSetting: Optional[str] = None
    transportFacility: Optional[str] = None
    wifiTechInfrastructure: Optional[str] = None
    coCurricularActivities: Optional[str] = None

class AcademicCredentials(BaseModel):
    educationBackground: EducationBackground
    academicMarks: AcademicMarks
    examPercentiles: ExamPercentiles
    reservationCategory: str
    achievementsExperience: Optional[AchievementsExperience] = None
    preferences: Preferences
    campusFacilitiesEnvironment: Optional[CampusFacilitiesEnvironment] = None
    annualBudget: float
    collegeTypePreferences: Optional[List[str]] = None
    priorityFactors: Optional[List[str]] = None

class RecommendationRequest(BaseModel):
    username: EmailStr
    academic_credentials: AcademicCredentials

class CollegeRecommendationRequest(BaseModel):
    category: str
    cet_percentile: float
    cet_course: List[str]
    location: Optional[List[str]] = None
    round: Optional[int] = Field(default=1)
    last_round_college_choice_code: Optional[int] = None

class SearchByChoiceCode(BaseModel):
    choice_code: int

class SearchByCollegeName(BaseModel):
    college_name: str

class SearchByCollegeCode(BaseModel):
    college_code: int

class CollegeDetails(BaseModel):
    username: EmailStr
    college_name: str
    college_code: int
    course_name: str
    course_code: Optional[int] = None
    choice_code: int
    round: int
    location: str
    category: str
    cet_percentile: float

class CollegeRecommendationGroupResponse(BaseModel):
    username: EmailStr
    Dream: list[dict]
    Reach: list[dict]
    Match: list[dict]
    Safety: list[dict]
    Round:int = Field(default=1)
    is_payment: bool
    accept_payment: bool

class CollegeRecommendationListResponse(BaseModel):
    message: Optional[str] = None
    success: bool = False
    data: CollegeRecommendationGroupResponse

class AICapDetailsResponseSchema(BaseModel):
    message: str
    success: bool
    data: RecommendationRequest
