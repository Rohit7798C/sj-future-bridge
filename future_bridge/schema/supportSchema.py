from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any

from future_bridge.models.supportModel import BulkAction, TicketStatus

from datetime import datetime


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

class ExportTicketsRequest(BaseModel):
    """
    Schema for filtering/exporting support tickets.
    """
    status: Optional[TicketStatus] = Field(None, description="Filter by ticket status (Open, Closed, InProgress, InDevelopment)")
    ticket_ids: Optional[List[str]] = Field(None, description="List of ticket IDs to export")

class BulkActionRequest(BaseModel):
    """
    Schema for performing bulk actions on tickets.
    """
    action: BulkAction
    ticket_ids: List[str]

class TicketFilterRequest(BaseModel):
    """
    Schema for filtering tickets in pagination API.
    """
    status: Optional[TicketStatus] = None
    sort: Optional[str] = "created_at:desc"
    page: int = 1
    limit: int = 10


class CommentRequest(BaseModel):
    """
    Schema for user adding comment on a ticket
    """
    ticket_id: str
    comment: str


class CommentResponse(BaseModel):
    """
    Response after user adds a comment
    """
    message: str
    success: bool
    data: Dict[str, Any]


class AdminCommentRequest(BaseModel):
    """
    Schema for admin adding comment on a ticket
    """
    ticket_id: str
    comment: str


class AdminCommentResponse(BaseModel):
    """
    Response after admin adds a comment
    """
    message: str
    success: bool
    data: Dict[str, Any]
