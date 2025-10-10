from fastapi import APIRouter, HTTPException, Depends, Request
import logging

from future_bridge.services.errorService import UserAlreadyExistsError
from future_bridge.services.userService import UserService, get_user_service
from future_bridge.schema.userSchema import UserRequest, UserResponse,FeedBack ,RoundPreferences
from future_bridge.config.messages import ErrorMessages
from future_bridge.utils.google.token_validator import jwtBearer, get_token_from_header
from future_bridge.utils.google.token_validator import validate_google_token
from future_bridge.schema.recommendationSchema import CollegeDetails
router = APIRouter()


@router.post("/store_user/", tags=["User"], response_model=UserResponse, summary="Store user in database")
async def store_user(
    request: UserRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    Store user data in the CJ_DATABASE user collection.
    """
    try:
        result = await user_service.store_user(request)
        return UserResponse(
            message="User stored successfully.",
            success=True,
            data=result
        )
    except UserAlreadyExistsError as e:
        logging.error(f"User already exists: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        logging.error(f"Validation error in store_user: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logging.error(f"Unexpected error in store_user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while storing user.") 


@router.post("/feedback", tags=["User"], response_model=UserResponse, summary="Store user Feedback in database")
async def store_user(
    request: FeedBack,
    user_service: UserService = Depends(get_user_service)
):
    """
    Store user feedback data in the CJ_DATABASE user collection.
    """
    try:
        result = await user_service.store_feedback(request)
        return UserResponse(
            message="Feedback stored successfully.",
            success=True,
            data=result
        )       
    except ValueError as e:
        logging.error(f"Validation error in store_feedback: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logging.error(f"Unexpected error in store_feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while storing feedback.")



@router.post('/store_college_details', tags=["User"],dependencies=[Depends(jwtBearer())], response_model=UserResponse, summary="Store college details in database")
async def store_college_details(
    payload: CollegeDetails,
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Store college details data in the CJ_DATABASE user collection.
    """
    try:
        token = get_token_from_header(request)
        validation_result = validate_google_token(token)
        is_valid = validation_result[0]
        email = validation_result[1]
        if not is_valid:
            raise ValueError("Invalid token.")
        # Validate the payload
        if not payload.username:
            raise ValueError("Username is required.")
        if not payload.college_name:
            raise ValueError("College name is required.")
        if not payload.college_code:
            raise ValueError("College code is required.")
        if not payload.course_name:
            raise ValueError("Course name is required.")
        if not payload.course_code:
            raise ValueError("Course code is required.")
        if not payload.choice_code:
            raise ValueError("Choice code is required.")
        if not payload.round:
            raise ValueError("Round is required.")
        result = await user_service.store_college_details(payload,email)
        return UserResponse(
            message="College details stored successfully.",
            success=True,
            data=result
        )
    except ValueError as e:
        logging.error(f"Validation error in store_college_details: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logging.error(f"Unexpected error in store_college_details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while storing college details.")

@router.get('/get_user_round_details/{round}', tags=["User"],dependencies=[Depends(jwtBearer())], response_model=UserResponse, summary="Get user round details from database")
async def get_user_round_details(
    request: Request,
    round:int,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get user round details from the CJ_DATABASE user collection.
    """
    try:
        token = get_token_from_header(request)
        validation_result = validate_google_token(token)
        is_valid = validation_result[0]
        email = validation_result[1]
        if not is_valid:
            raise ValueError("Invalid token.")
        result = await user_service.get_user_round_details(email,round)

        return UserResponse(
            message="User round details retrieved successfully.",
            success=True,
            data=result
        )
    except ValueError as e:
        logging.error(f"Validation error in get_user_round_details: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logging.error(f"Unexpected error in get_user_round_details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while retrieving user round details.")


@router.post('/round_prefrences', tags=["User"],dependencies=[Depends(jwtBearer())], response_model=UserResponse, summary="Store user round preferences in database")
async def store_user_round_preferences(
    payload: RoundPreferences,
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Store user round preferences in the CJ_DATABASE user collection.
    """
    try:
        token = get_token_from_header(request)
        validation_result = validate_google_token(token)
        is_valid = validation_result[0]
        email = validation_result[1]
        if not is_valid:
            raise ValueError("Invalid token.")
        result = await user_service.store_user_round_preferences(payload,email)
        return UserResponse(
            message="User round preferences stored successfully.",
            success=True,
            data=result
        )  
    except ValueError as e:
        logging.error(f"Validation error in store_user_round_preferences: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logging.error(f"Unexpected error in store_user_round_preferences: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while storing user round preferences.")

@router.get('/get_user_round_preferences/{round}', tags=["User"],dependencies=[Depends(jwtBearer())], response_model=UserResponse, summary="Get user round preferences from database")
async def get_user_round_preferences(
    request: Request,
    round:int,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get user round preferences from the CJ_DATABASE user collection.
    """
    try:
        token = get_token_from_header(request)
        validation_result = validate_google_token(token)
        is_valid = validation_result[0]
        email = validation_result[1]
        if not is_valid:
            raise ValueError("Invalid token.")
        result = await user_service.get_user_round_preferences(email,round)
        return UserResponse(
            message="User round preferences retrieved successfully.",
            success=True,
            data=result
        )
    except ValueError as e:
        logging.error(f"Validation error in get_user_round_preferences: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logging.error(f"Unexpected error in get_user_round_preferences: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while retrieving user round preferences.")






