from typing import List, Optional, Dict, Any, Union, TypeVar
from pydantic import BaseModel, Field, HttpUrl
from fastapi import Query

class PlacementRange(BaseModel):
    min: Optional[float]
    max: Optional[float]

class CETCutoffRange(BaseModel):
    min: Optional[float]
    max: Optional[float]

class CollegeSummaryResponse(BaseModel):
    college_name: str
    college_type: str
    institute_id: Optional[str] = None
    sj_institute_id: Optional[str] = None
    city: str
    logo: str
    rating: Optional[float] = None
    courses_count: int
    courses: Optional[List[str]] = None
    total_intake: Optional[int]
    fees: Optional[int]
    placement_range: PlacementRange
    cet_cutoff_range: CETCutoffRange

class SearchCollegesQuery(BaseModel):
    """
    Schema for searching colleges with sorting options.
    """
    college_name: Optional[List[str]] = Field(None, description="List of college names (exact or partial)")
    course: Optional[List[str]] = Field(None, description="List of course names (branch)")
    city: Optional[List[str]] = Field(None, description="List of city names")
    sort_by: Optional[str] = Field(None, description='Sort by "cutoff_cet" or "placement_percentage"')
    order: Optional[str] = Field(None, description='"asc" or "desc"')
    
    def __iter__(self):
        """Enable dict-like iteration for extracting additional filters."""
        for key, value in self.__dict__.items():
            yield key, value

class InstituteMeta(BaseModel):
    College_Name: str
    College_Website: Optional[str] = None
    College_Address: Optional[str] = None
    City: Optional[str] = None
    College_Type: Optional[str] = None
    NAAC_Acrredition: Optional[str] = None
    University_Affiliation: Optional[str] = None
    Courses_Offered: Optional[str] = None
    Overall_College_Placement_Percentage: Optional[float] = None
    Student_Intake: Optional[int] = None
    Admission_Remarks: Optional[str] = None
    College_Hostel_Available: Optional[str] = None
    Annual_Fees_INR: Optional[int] = Field(None, alias="Annual_Fees_(INR)")
    Previous_Year_Highest_Package_Offered_LPA: Optional[float] = Field(None, alias="Previous_Year_Highest_Package_Offered_(LPA)")
    College_Working_Hours: Optional[str] = None
    Lab_Facilities: Optional[str] = None
    College_Reviews_out_of_5: Optional[float] = None
    College_Bus_Facility_Available: Optional[str] = None
    Nearest_Airport: Optional[str] = None
    Distance_from_Airport: Optional[float] = None
    Nearest_Railway_Station: Optional[str] = None
    Distance_from_Railway_Station: Optional[float] = None
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
    College_Code: Optional[str] = None
    SJ_Institute_Code: int
    College_Logo: Optional[str] = None

class DepartmentMeta(BaseModel):
    College_Name: str
    NBA_Accredited: Optional[str] = None
    Courses_Offered: Optional[str] = None
    Placement_Percentage: Optional[float] = None
    Student_Intake: Optional[int] = None

class CutoffMeta(BaseModel):
    College_Name: str
    Course_Name: Optional[str] = None
    Year: Optional[int] = None
    # Add all possible cutoff fields as Optional[float]
    GOPENS: Optional[float] = None
    GSCS: Optional[float] = None
    GSTS: Optional[float] = None
    GVJS: Optional[float] = None
    GNT1S: Optional[float] = None
    GNT2S: Optional[float] = None
    GOBCS: Optional[float] = None
    GSEBCS: Optional[float] = None
    LOPENS: Optional[float] = None
    LSCS: Optional[float] = None
    LSTS: Optional[float] = None
    LVJS: Optional[float] = None
    LNT2S: Optional[float] = None
    LNT3S: Optional[float] = None
    LOBCS: Optional[float] = None
    LSEBCS: Optional[float] = None
    DEFOPENS: Optional[float] = None
    DEFOBCS: Optional[float] = None
    TFWS: Optional[float] = None
    EWS: Optional[float] = None

class CourseCutoffGroup(BaseModel):
    course_name: str
    cutoffs: List[CutoffMeta]

class CollegeDetailResponse(BaseModel):
    institute_meta: InstituteMeta
    departments: List[DepartmentMeta]
    cutoff_data: List[CourseCutoffGroup]

class SearchCollegesData(BaseModel):
    colleges: List[CollegeSummaryResponse]
    cities: List[str]
    total_records: int

class SearchCollegesResponse(BaseModel):
    message: str
    success: bool
    data: SearchCollegesData

class AdmissionChancesRequest(BaseModel):
    """
    Schema for admission chances calculation request.
    """
    sj_institute_id: int = Field(..., description="SJ Institute Code")
    course_name: str = Field(..., description="Course name")
    cet_percentile: float = Field(..., description="Student's CET percentile", ge=0, le=100)
    category: str = Field(default="GOPENS", description="Category for cutoff (e.g., GOPENS, GSCS, GSTS, etc.)")

class AdmissionChancesResponse(BaseModel):
    """
    Schema for admission chances calculation response.
    """
    college_name: str
    course_name: str
    category: str
    student_cet_percentile: float
    last_year_cutoff: float
    cutoff_year: int
    admission_probability: int
    probability_message: str