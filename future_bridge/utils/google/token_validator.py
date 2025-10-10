from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging 
from functools import wraps

from future_bridge.utils.google.token_validation import validate_google_token
from future_bridge.config.messages import ErrorMessages

class jwtBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(jwtBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials : HTTPAuthorizationCredentials = await super(jwtBearer,self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            token =  credentials.credentials
            is_valid = self.verify_token(token)
            if not is_valid:
                raise HTTPException(status_code=403, detail="Invalid Token.")
            return token
        else:
            raise HTTPException(status_code=403, detail="Invalid Authorization header.")
    
    def verify_token(self, token):
        is_valid, email = validate_google_token(token)
        return is_valid


def token_validator(func_to_decorate):
    @wraps(func_to_decorate)
    async def decorator_wrapper(request: Request, *args, **kwargs):
        try:
            # Get the token from the request headers
            token = request.headers.get('Authorization')
            if not token:
                raise HTTPException(status_code=401, detail=ErrorMessages.ERROR_TOKEN_MISSING)

            # Validate the token
            token = token.split()[1] if token.startswith('Bearer') else None
            if not token or not validate_google_token(token):
                raise HTTPException(status_code=401, detail=ErrorMessages.ERROR_TOKEN_INVALID)

            # Call the original function and return its response
            return await func_to_decorate(request, *args, **kwargs)
        except Exception as e:
            logging.error(f'Encountered an error during token validation: {str(e)}')
            raise HTTPException(status_code=500, detail=ErrorMessages.ERROR_TOKEN_VALID)

    return decorator_wrapper


def get_token_from_header(req:Request) -> str: 
    """
    Extracts token from the header

    Args:
        req (HTTP Request ): Http request with Authorization token in header
    """
    
    # Extract token from the header
    token = req.headers.get('Authorization')
    if not token:
        return  "Authorization Token is missing"
    token = token.split()[1] if token.startswith('Bearer') else None
    
    return token
