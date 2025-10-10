from fastapi import APIRouter, File, HTTPException, Depends, Request, UploadFile, Form
from fastapi.responses import JSONResponse
import logging
import re
import json

from future_bridge.utils.JWTTokenGenrator import create_jwt
from future_bridge.utils.sendEmail import MicrosoftEmailService
from future_bridge.services.commonService import OTPService, get_otp_service
from future_bridge.schema.commonSchema import ValidateOtpResponse,ValidateOtpBody,ResponseSchema,EmailSchema
from future_bridge.config.messages import ErrorMessages

router = APIRouter()


@router.post("/sendOTP", tags=["Auth"], response_model=ResponseSchema)
async def send_otp(request: EmailSchema):
    logging.info("Processing request for sendOTP.")
    email = request.email

    try:
        response:ResponseSchema = await MicrosoftEmailService().send_otp(email)

        return response
    except Exception as e:
        logging.error(f"Error in sendOTP: {e}")
        if str(e).startswith("cannot unpack non-iterable bool object"):
            raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_TOKEN_EXPIRY, "technicalError": str(e)})
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_WHILE_FETCH, "technicalError": str(e)})

@router.post("/validateOTP", tags=["Auth"], response_model=ValidateOtpResponse)
async def validate_otp(
    otp_request: ValidateOtpBody,
    otp_service: OTPService = Depends(get_otp_service)
):
    
    logging.info("Processing request for validateOTP.")
    email = otp_request.email
    otp = otp_request.otp
    user_type = otp_request.user_type

    try:
        response:ValidateOtpResponse = await otp_service.validateUser(email, otp, user_type)
        return response
    except Exception as e:
        logging.error(f"Error in validateOTP: {e}")
        if str(e).startswith("cannot unpack non-iterable bool object"):
            raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_TOKEN_EXPIRY, "technicalError": str(e)})
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_WHILE_FETCH, "technicalError": str(e)})