from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from typing import Optional
from datetime import datetime

class User(BaseModel):
    """
    Data model representing a user.
    """
    username: str
    name: Optional[str] = ""
    profileIcon: Optional[str] = ""
    user_level: str = 'Standard'  # Default level set to "Standard"
    questionnaire: Optional[list] = None
    resume: Optional[list] = []
    mobile: Optional[int] = Field(None, gt=1000000000, lt=9999999999)
    answers: Optional[dict] = {}
    user_origin: str = "Future Bridge"

    def __str__(self) -> str:
        return self.username
    
class Feedback(BaseModel):
    """
    Data model representing a feedback.
    """
    username: str
    feedback: Optional[str] = ""
    rating: Optional[int] = Field(None, gt=0, lt=6)

class RoundPreferences(BaseModel):
    """
    Data model representing a round preferences.
    """
    username: str
    round: int
    branches: list[str]
    cities: list[str]
    timestamp: datetime = datetime.now()

class DiplomaUserConfig(BaseModel):
    """
    Data model representing a diploma user config.
    """
    category: str
    cet_percentile: float
    cet_course: List[str]
    location: Optional[List[str]] = None
    round: Optional[int] = Field(default=1)
    last_round_college_choice_code: Optional[int] = None
    timestamp: datetime = datetime.now()
    
