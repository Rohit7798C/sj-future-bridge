from fastapi import APIRouter, HTTPException, Depends,Request
import logging
from future_bridge.schema.commonSchema import *
from future_bridge.utils.google.token_validator import jwtBearer, get_token_from_header
from future_bridge.utils.google.token_validation import validate_google_token
from future_bridge.services.commonService import CommonService, get_common_service

router = APIRouter()

@router.post('/college/configuration', tags=["Common"],dependencies=[Depends(jwtBearer())], response_model=dict, summary="Stores the users college admission configuration")
async def store_college_configuration(
    payload:  CollegeConfigurationRequest,
    request: Request,
    common_service: CommonService = Depends(get_common_service),
):
    try:
        token = get_token_from_header(request)
        isvalid,email=validate_google_token(token)
        if not isvalid:
            raise HTTPException(status_code=400, detail="Invalid token")
        await common_service.store_college_config(payload,email)
        return {"success":True,"data":payload,"message":"College configuration stored successfully"}
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=400, detail="Invalid token")



@router.get('/college/configuration', tags=["Common"],dependencies=[Depends(jwtBearer())], response_model=dict, summary="Get the users college admission configuration")
async def get_college_configuration(
request: Request,
common_service: CommonService = Depends(get_common_service),
):
    try:
        token = get_token_from_header(request)
        isvalid,email=validate_google_token(token)
        if not isvalid:
            raise HTTPException(status_code=400, detail="Invalid token")
        config=await common_service.get_college_config(email)
        if not config:
            raise ValueError("College configuration not found")

        return {"success":True,"data":config,"message":"College configuration fetched successfully"}
    except ValueError as e:
        logging.error(e)
        raise HTTPException(status_code=404, detail="College configuration not found")
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=400, detail="Invalid exam type")    


@router.post('/store/round_preferences_and_generate_recommendations', tags=["Common"],dependencies=[Depends(jwtBearer())], 
response_model=dict, summary="Stores the users round preferences and generates recommendations")
async def store_round_preferences(
request: Request,
payload: RoundPreferencesRequest,
common_service: CommonService = Depends(get_common_service),
):
    try:
        token = get_token_from_header(request)
        isValid,email=validate_google_token(token)
        if not isValid:
            raise HTTPException(status_code=400, detail="Invalid token")
        await common_service.store_round_preferences(payload,email)
        recommendations=await common_service.generate_recommendations(payload,email)
        if not recommendations:
            raise ValueError("Recommendations not found")
        return {"success":True,"data":recommendations,"message":"Recommendations generated successfully"}   
    except ValueError as e:
        logging.error(e)
        raise HTTPException(status_code=404, detail="Recommendations not found")
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=400, detail=f"{e}")


@router.get('/get/round_preferences/{round_no}/{exam_type}', tags=["Common"],dependencies=[Depends(jwtBearer())], 
response_model=dict, summary="Get the users round preferences")
async def get_round_preferences(
request: Request,
round_no: int,
exam_type: str,
common_service: CommonService = Depends(get_common_service),
):
    try:
        token = get_token_from_header(request)
        isvalid,email=validate_google_token(token)
        if not isvalid:
            raise HTTPException(status_code=400, detail="Invalid token")
        preferences=await common_service.get_round_preferences(round_no,email,exam_type)
        if not preferences:
            raise ValueError("Round preferences not found")
        recommendations=await common_service.get_recommendations(round_no=round_no,email=email,exam_type=exam_type)
        return {"success":True,"data":{"preferences":preferences,"recommendations":recommendations},"message":"Round preferences fetched successfully"}

    except ValueError as e:
        logging.error(e)
        raise HTTPException(status_code=404, detail="Round preferences not found")
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=400, detail=f"{e}") 


@router.get('/search_college_by_name/{exam_type}/{college_name}', tags=["Common"],dependencies=[Depends(jwtBearer())], 
response_model=dict, summary="Get the college details by name")
async def search_college_by_name(
request: Request,
exam_type: ExamType,
college_name: str,
common_service: CommonService = Depends(get_common_service),
):
    try:
        token = get_token_from_header(request)
        isvalid,email=validate_google_token(token)
        if not isvalid:
            raise HTTPException(status_code=400, detail="Invalid token")
        college=await common_service.search_college_by_name(college_name,exam_type)
        if not college:
            raise ValueError("College not found")
        return {"success":True,"data":college    ,"message":"College fetched successfully"}
    except ValueError as e:
        logging.error(e)
        raise HTTPException(status_code=404, detail="College not found")
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=400, detail=f"{e}")

@router.get('/search_college_by_college_code/{exam_type}/{college_code}', tags=["Common"],dependencies=[Depends(jwtBearer())], 
response_model=dict, summary="Get the college details by college code")
async def search_college_by_college_code(
request: Request,
exam_type: ExamType,
college_code: int,
common_service: CommonService = Depends(get_common_service),
):
    try:
        token = get_token_from_header(request)
        isvalid,email=validate_google_token(token)
        if not isvalid:
            raise HTTPException(status_code=400, detail="Invalid token")
        college=await common_service.search_college_by_college_code(college_code,exam_type)
        if not college:
            raise ValueError("College not found")
        return {"success":True,"data":college,"message":"College fetched successfully"}
    except ValueError as e:
        logging.error(e)
        raise HTTPException(status_code=404, detail="College not found")
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=400, detail=f"{e}") 

@router.get('/search_college_by_choice_code/{exam_type}/{choice_code}', tags=["Common"],dependencies=[Depends(jwtBearer())], 
response_model=dict, summary="Get the college details by choice code")
async def search_college_by_choice_code(
request: Request,
exam_type: ExamType,
choice_code: str,
common_service: CommonService = Depends(get_common_service),
):
    try:
        token = get_token_from_header(request)
        isvalid,email=validate_google_token(token)
        if not isvalid:
            raise HTTPException(status_code=400, detail="Invalid token")
        college=await common_service.search_college_by_choice_code(choice_code,exam_type)
        if not college:
            raise ValueError("College not found")
        return {"success":True,"data":college,"message":"College fetched successfully"}
    except ValueError as e:
        logging.error(e)
        raise HTTPException(status_code=404, detail="College not found")
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=400, detail=f"{e}") 



@router.post('/store_round_college_preference', tags=["Common"],dependencies=[Depends(jwtBearer())], 
response_model=dict, summary="Stores the users round preferences")
async def store_round_preferences(
request: Request,
payload: CollegeRoundPrefrence,
common_service: CommonService = Depends(get_common_service),
):
    try:
        token = get_token_from_header(request)
        isvalid,email=validate_google_token(token)
        if not isvalid:
            raise HTTPException(status_code=400, detail="Invalid token")
        await common_service.store_round_college_preference(payload,email)
        return {"success":True,"message":"Round preferences stored successfully"}
    except ValueError as e:
        logging.error(e)
        raise HTTPException(status_code=404, detail="Round preferences not stored")
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=400, detail=f"{e}") 

@router.get('/get_round_college_preferences/{round_no}/{exam_type}', tags=["Common"],dependencies=[Depends(jwtBearer())], 
response_model=dict, summary="Get the users round preferences")
async def get_round_preferences(
request: Request,
round_no: int,
exam_type: ExamType,
common_service: CommonService = Depends(get_common_service),
):
    try:
        token = get_token_from_header(request)
        isvalid,email=validate_google_token(token)
        if not isvalid:
            raise HTTPException(status_code=400, detail="Invalid token")
        preferences=await common_service.get_round_college_preferences(email,exam_type,round_no)
        if not preferences:
            raise ValueError("Round preferences not found")
        return {"success":True,"data":preferences,"message":"Round preferences fetched successfully"}
    except ValueError as e:
        logging.error(e)
        raise HTTPException(status_code=404, detail="Round preferences not found")
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=400, detail=f"{e}") 


