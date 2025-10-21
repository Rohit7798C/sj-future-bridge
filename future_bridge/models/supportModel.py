from enum import Enum
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

from typing import Optional
from datetime import datetime, timedelta, timezone

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now_naive() -> datetime:
    return datetime.now(IST).replace(tzinfo=None)

class TicketStatus(str, Enum):
    """
    Enum representing valid support ticket statuses.
    """
    OPEN = "Open"
    CLOSED = "Closed"
    IN_PROGRESS = "InProgress"
    IN_DEVELOPMENT = "InDevelopment"

class BulkAction(str, Enum):
    CLOSE = "close"
    DELETE = "delete"
    MARK_PAID = "mark_paid"

class Support(BaseModel):
    """
    Data model representing a user tickets.
    """
    ticket_id: Optional[str] = None
    username: EmailStr
    name: str
    product_type: str = 'Standard'
    user_origin: str = "Future Bridge"
    details: str
    attachments: Optional[List[str]] = []
    browser_info: Optional[str] = None
    created_at: datetime = Field(default_factory=get_ist_now_naive)
    status: TicketStatus = TicketStatus.OPEN
    is_paid: bool = False

    def __str__(self) -> str:
        return self.username
