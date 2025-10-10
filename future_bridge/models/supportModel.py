from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

from typing import Optional
from datetime import datetime, timedelta, timezone

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now_naive() -> datetime:
    return datetime.now(IST).replace(tzinfo=None)

class Support(BaseModel):
    """
    Data model representing a user tickets.
    """
    username: EmailStr
    name: str
    product_type: str = 'Standard'
    user_origin: str = "Future Bridge"
    details: str
    attachments: Optional[List[str]] = []
    browser_info: Optional[str] = None
    created_at: datetime = Field(default_factory=get_ist_now_naive)
    status: str = "Open"
    is_paid: bool = False

    def __str__(self) -> str:
        return self.username
