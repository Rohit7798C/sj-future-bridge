import csv
import io
from typing import List, Optional
from fastapi import APIRouter,Form, File, HTTPException, Depends, Query, Request, UploadFile
import logging

from fastapi.responses import StreamingResponse

from future_bridge.schema.supportSchema import BulkActionRequest, ExportTicketsRequest, SupportRequest, SupportResponse, TicketFilterRequest
from future_bridge.services.supportService import SupportService, get_support_service
from future_bridge.utils.google.token_validator import jwtBearer, get_token_from_header
from future_bridge.utils.google.token_validator import validate_google_token
from future_bridge.schema.supportSchema import CommentRequest, CommentResponse, AdminCommentRequest, AdminCommentResponse

router = APIRouter()

ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png", "mp4", "mov", "avi"}
MAX_FILE_SIZE_MB = 20

@router.post('/raise_issues', tags=["Support"], dependencies=[Depends(jwtBearer())], response_model=SupportResponse, summary="Store user tickets in database")
async def store_user_tickets(
    request: Request,
    payload: SupportRequest = Depends(),
    files: List[UploadFile] = File(None),
    support_service: SupportService = Depends(get_support_service)
):
    """
    Store user support tickets in the `support_issues` collection.

    - Validates JWT token and file attachments.
    - Uploads valid files to Azure Blob Storage.
    - Persists ticket data using the service layer.
    - Returns a success message with ticket details.
    """
    try:
        token = get_token_from_header(request)
        is_valid = validate_google_token(token)
        if not is_valid:
            raise ValueError("Invalid token.")
        
        # Capture browser/system info
        browser_info = request.headers.get("user-agent", "Unknown")

        # Validate attachments
        blob_ids = []
        if files:
            if len(files) > 2:
                raise ValueError("Max 2 attachments allowed.")
            
            for file in files:
                ext = file.filename.split(".")[-1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    raise ValueError(f"Invalid file type: {file.filename}. Allowed: {ALLOWED_EXTENSIONS}")

                # Size validation
                contents = await file.read()
                if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
                    raise ValueError(f"{file.filename} exceeds {MAX_FILE_SIZE_MB}MB limit.")

                # Upload to Azure Blob and store blob ID
                blob_id = await support_service.upload_to_blob(file.filename, contents)
                blob_ids.append(blob_id)

        result = await support_service.store_user_tickets(payload, browser_info, blob_ids)

        return SupportResponse(
            message = "User tickets stored successfully.",
            success = True,
            data = result
        )
    except ValueError as e:
        logging.error(f"Validation error in raise_issues: {str(e)}")
        raise HTTPException(status_code = 422, detail = str(e))
    except Exception as e:
        logging.error(f"Unexpected error in raise_issues: {str(e)}", exc_info=True)
        raise HTTPException(status_code = 500, detail="An unexpected error occurred while storing user ticket.")

# Fetch all tickets (with filters/sorting/pagination)
@router.get("/tickets", tags=["Support"], dependencies=[Depends(jwtBearer())], response_model=SupportResponse, summary="Fetch all support tickets")
async def get_all_tickets(
    filters: TicketFilterRequest = Depends(),
    support_service: SupportService = Depends(get_support_service)
):
    """
    Retrieve all support tickets with optional filters and pagination.

    Args:
        status (str, optional): Filter tickets by status.
        sort (str): Sort field and direction (e.g., 'created_at:desc').
        page (int): Page number for pagination.
        limit (int): Maximum records per page.
    """
    try:
        tickets_data = await support_service.get_all_tickets(
            filters.status.value if filters.status else None,
            filters.sort,
            filters.page,
            filters.limit
        )
        return SupportResponse(message="Tickets fetched successfully", success=True, data=tickets_data)
    except Exception as e:
        logging.error(f"Error fetching tickets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
# Fetch single ticket by ID
@router.get("/tickets/{ticket_id}", tags=["Support"], dependencies=[Depends(jwtBearer())], response_model=SupportResponse, summary="Fetch single support ticket details")
async def get_ticket_by_id(
    ticket_id: str,
    support_service: SupportService = Depends(get_support_service)
):
    """
    Fetch details of a single support ticket by its unique ID.
    Args:
        ticket_id (str): Unique ticket ID.
    """
    try:
        ticket = await support_service.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return SupportResponse(message="Ticket fetched successfully", success=True, data=ticket)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching ticket details")

# Export tickets as CSV
@router.post("/tickets-export", tags=["Support"], dependencies=[Depends(jwtBearer())], summary="Export support tickets as CSV")
async def export_tickets_as_csv(
    request: ExportTicketsRequest,
    support_service: SupportService = Depends(get_support_service)
):
    """
    Export all or filtered support tickets as a downloadable CSV file.
    Args:
        request (ExportTicketsRequest): Filter options (status, ticket_id).
    """
    try:
        # Generate CSV stream from service
        csv_output = await support_service.export_tickets_as_csv(
            status=request.status.value if request.status else None,
            ticket_ids=request.ticket_ids
        )

        return StreamingResponse(
            csv_output,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=support_tickets.csv"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error exporting tickets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

# Bulk action on tickets
@router.patch("/tickets/bulk-action", tags=["Support"], dependencies=[Depends(jwtBearer())], response_model=SupportResponse, summary="Perform bulk actions on tickets")
async def bulk_action_on_tickets(
    body: BulkActionRequest,
    support_service: SupportService = Depends(get_support_service)
):
    """
    Perform bulk actions (close, delete, mark_paid) on multiple tickets.
    Args:
        action (str): The bulk action to perform. (action: close --> status=Closed OR action: delete --> ticket is deleted, OR action: mark_paid --> is_paid: true)
        ticket_ids (List[str]): List of ticket IDs.
    """
    try:
        result = await support_service.perform_bulk_action(body.action, body.ticket_ids)
        return SupportResponse(message="Bulk action completed", success=True, data=result)
    except Exception as e:
        logging.error(f"Error in bulk action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error performing bulk action")

# Metrics API
@router.get("/metrics", tags=["Support"], dependencies=[Depends(jwtBearer())], response_model=SupportResponse, summary="Fetch dashboard metrics")
async def get_support_metrics(
    support_service: SupportService = Depends(get_support_service)
):
    """
    Fetch key dashboard metrics including open, closed, paid, and total tickets.
    """
    try:
        metrics = await support_service.get_support_metrics()
        return SupportResponse(message="Metrics fetched successfully", success=True, data=metrics)
    except Exception as e:
        logging.error(f"Error fetching metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching metrics")
    
# Helper function inside supportRouters.py (or import from a utils file)
def extract_user_info_from_token(token: str) -> dict:
    result = validate_google_token(token)

    if isinstance(result, tuple) and len(result) == 2:
        is_valid, email = result
        if is_valid and email:
            return {"email": email}
        else:
            raise ValueError("Invalid token.")
    elif isinstance(result, dict):
        if result.get("is_valid") and result.get("email"):
            return {"email": result.get("email")}
        else:
            raise ValueError("Invalid token format or missing email.")
    else:
        raise ValueError("Unexpected token validation response format.")

# GET endpoint -> /support/my_tickets
@router.get('/my_tickets', tags=["Support"], dependencies=[Depends(jwtBearer())], summary="Fetch user support tickets")
async def get_user_tickets(
    request: Request, support_service: SupportService = Depends(get_support_service)
):
    try:
        # Extract token and user info
        token = get_token_from_header(request)
        user_info = extract_user_info_from_token(token)

        # Get user email
        user_email = user_info.get("email")
        if not user_email:
            raise ValueError("Email not found in token.")
        
        # Fetch tickets
        tickets = await support_service.get_user_tickets(user_email)
        return {
            "message": "User tickets fetched successfully.",
            "success": True,
            "data": tickets
        }
    except ValueError as e:
        logging.error(f"Validation error in get_user_tickets: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logging.error(f"Unexpected error in get_user_tickets: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching user tickets.")


# POST endpoint -> /support/add_comment
@router.post('/add_comment', tags=["Support"], dependencies=[Depends(jwtBearer())], response_model=CommentResponse, summary="Add a comment to a ticket")
async def add_comment_to_ticket(
    request: Request,
    # Changes for adding the images and videos
    ticket_id: str = Form(...),
    comment: str = Form(...),
    files: List[UploadFile] = File(default=[]),
    support_service: SupportService = Depends(get_support_service)
):
    """
    Add a comment to an existing ticket.
    """
    try:
        # Extract token and user info
        token = get_token_from_header(request)
        user_info = extract_user_info_from_token(token)
        user_email = user_info.get("email")
        if not user_email:
            raise ValueError("Email not found in token.")
        
        # Adding the code for the File Uploading part.
        # Allowed extensions & size limit
        blob_ids = []
        if files:
            blob_ids = await support_service.validate_and_upload_files(files, max_size_mb=100, max_files=2)

        # Then pass blob_ids to your service method
        result = await support_service.add_comment(user_email, ticket_id, comment, blob_ids)

        return CommentResponse(
            message="Comment added successfully.",
            success=True,
            data=result
        )
    except ValueError as e:
        logging.error(f"Validation error in add_comment_to_ticket: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logging.error(f"Unexpected error in add_comment_to_ticket: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while adding comment.")


# POST Endpoint for admin Adding the comment -> '/admin/add_comment'
@router.post('/admin/add_comment', tags=["Support"], dependencies=[Depends(jwtBearer())], response_model=AdminCommentResponse, summary="Admin adds a comment to a ticket")
async def add_comment_by_admin(
    request: Request,
    payload: AdminCommentRequest,
    support_service: SupportService = Depends(get_support_service)
):
    """
    Admin adds a comment to an existing ticket.
    """
    try:
        # Extract token and user info
        token = get_token_from_header(request)
        user_info = extract_user_info_from_token(token)
        user_email = user_info.get("email")
        if not user_email:
            raise ValueError("Email not found in token.")

        # Optional: check if user is admin
        if not await support_service.is_admin(user_email):
            raise ValueError("Unauthorized: Only admins can comment here.")

        result = await support_service.add_comment_by_admin(user_email, payload.ticket_id, payload.comment)
        return AdminCommentResponse(
            message="Admin comment added successfully.",
            success=True,
            data=result
        )
    except ValueError as e:
        logging.error(f"Validation error in add_comment_by_admin: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logging.error(f"Unexpected error in add_comment_by_admin: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while adding admin comment.")
