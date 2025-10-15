from typing import List
from fastapi import APIRouter, File, HTTPException, Depends, Request, UploadFile
import logging

from future_bridge.schema.supportSchema import SupportRequest, SupportResponse
# for Adding the Comment
from future_bridge.schema.supportSchema import CommentRequest, CommentResponse
# for admin Adding the Comment
from future_bridge.schema.supportSchema import AdminCommentRequest, AdminCommentResponse
from future_bridge.services.supportService import SupportService, get_support_service
from future_bridge.utils.google.token_validator import jwtBearer, get_token_from_header
from future_bridge.utils.google.token_validator import validate_google_token
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
    Store user tickets in the FB_DATABASE support_issues collection.
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


# Helper function inside supportRouters.py (or import from a utils file)
def extract_user_info_from_token(token: str) -> dict:
    """
    Validate token and return user info dictionary.
    Raises ValueError if token is invalid.
    """
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
    request: Request,
    support_service: SupportService = Depends(get_support_service)
):
    """
    Fetch all support tickets of the logged-in user from the database.
    """
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
    payload: CommentRequest,
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

        result = await support_service.add_comment(user_email, payload.ticket_id, payload.comment)

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

