from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

class SupportRequest(BaseModel):
    """
    Request model for storing user tickets
    """
    username: EmailStr
    name: str
    product_type: str = 'Standard'
    user_origin: str = "Future Bridge"
    details: str

class SupportResponse(BaseModel):
    """
    Response model for Support user tickets
    """
    message: str
    success: bool
    data: Dict[str, Any] 
