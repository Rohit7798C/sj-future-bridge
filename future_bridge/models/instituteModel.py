from typing import List, Dict, Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

class CollegeModel(BaseModel):
    """
    Pydantic model for college data structure.
    """
    College_Name: str
    College_Website: str
    College_Address: Optional[str] = None
    City: str
    College_Type: str
    NAAC_Acrredition: Optional[str] = None
    University_Affiliation: Optional[str] = None
    Courses_Offered: Optional[str] = None
    Overall_College_Placement_Percentage: Optional[int] = None
    Student_Intake: Optional[int] = None
    College_Hostel_Available: Optional[str] = None
    Annual_Fees_INR: Optional[int] = Field(None, alias="Annual_Fees_(INR)")
    Annual_Hostel_Fees_INR: Optional[int] = Field(None, alias="Annual_Hostel_Fees_(INR)")
    Previous_Year_Highest_Package_Offered_LPA: Optional[int] = Field(
        None, alias="Previous_Year_Highest_Package_Offered_(LPA)"
    )
    College_Working_Hours: Optional[str] = None
    Lab_Facilities: Optional[str] = None
    College_Reviews_out_of_5: Optional[float] = None
    College_Bus_Facility_Available: Optional[str] = None
    Nearest_Airport: Optional[str] = None
    Distance_from_Airport: Optional[int] = None
    Nearest_Railway_Station: Optional[str] = None
    Distance_from_Railway_Station: Optional[int] = None
    College_Entrance_Exam: Optional[str] = None
    MHT_CET_Accepted: Optional[str] = None
    JEE_Mains_Accepted: Optional[str] = None
    Scholarships_Offered: Optional[str] = None
    Sports_Facilities: Optional[str] = None
    Internship_Programs: Optional[str] = None
    Faculty_Student_Ratio: Optional[str] = None
    Alumni_Connect: Optional[str] = None
    References: Optional[str] = None
    NIRF_Rank_Min: Optional[int] = None
    NIRF_Rank_Max: Optional[int] = None
    Top_Recruiters: Optional[List[str]] = None
    
    class Config:
        populate_by_name = True  # Allow population by alias

class InstituteModel:
    """
    Model for transforming institute data.
    """
    @staticmethod
    def transform_institute_data(institute_data: Dict) -> Dict:
        """
        Transform a single institute document.
        
        Args:
            institute_data: Raw institute data from the database
            
        Returns:
            Transformed institute data
        """
        # Validate and transform the data using the Pydantic model
        try:
            # This will validate the data against the model
            college = CollegeModel(**institute_data)
            # Return the model as a dict
            return college.model_dump(by_alias=True)
        except Exception as e:
            # If validation fails, return the original data
            # In a production environment, you might want to log this error
            return institute_data
    
    @staticmethod
    def transform_institutes_list(institutes_data: List[Dict]) -> List[Dict]:
        """
        Transform a list of institute documents.
        
        Args:
            institutes_data: List of raw institute data from the database
            
        Returns:
            List of transformed institute data
        """
        return [InstituteModel.transform_institute_data(institute) for institute in institutes_data]