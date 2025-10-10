from typing import List
from fastapi import APIRouter, File, HTTPException, Depends, Request, UploadFile
import logging

from future_bridge.schema.supportSchema import SupportRequest, SupportResponse
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