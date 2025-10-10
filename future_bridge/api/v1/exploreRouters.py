from fastapi import FastAPI, HTTPException, APIRouter, Query, Depends, status, Request
from typing import Dict, Optional, List, Any
import logging
from future_bridge.services.exploreServices import explore_Service, ExploreService
from future_bridge.schema.instituteSchema import SearchCollegesQuery, AdmissionChancesRequest
from future_bridge.schema.commonSchema import ResponseSchema
from future_bridge.config.messages import ErrorMessages
from future_bridge.utils.google.token_validator import jwtBearer, get_token_from_header
from future_bridge.utils.google.token_validation import validate_google_token

from future_bridge.services.recommendationService import recommendation_service, RecommendationService
from future_bridge.schema.recommendationSchema import RecommendationRequest, CollegeRecommendationRequest, CollegeRecommendationListResponse, AICapDetailsResponseSchema
from future_bridge.schema.recommendationSchema import SearchByChoiceCode , SearchByCollegeName ,SearchByCollegeCode

router = APIRouter()

@router.post("/Quick_College_Scan/", tags=["Colleges"], response_model=ResponseSchema, summary="Search for colleges")
async def search_colleges(
    query: SearchCollegesQuery,
    explore_service: ExploreService = Depends(explore_Service)
):
    """
    Endpoint to search for colleges with optional sorting and support for multiple cities, colleges, and courses.
    
    Parameters:
    - **college_name**: Optional list of college names (exact or partial match supported)
    - **course**: Optional list of course names (branch)
    - **city**: Optional list of city names
    - **sort_by**: Optional field to sort by ("cutoff_cet" or "placement_percentage")
    - **order**: Optional sort order ("asc" or "desc")
    - Additional filters can be passed as query parameters
    
    Returns:
    - **ResponseSchema**: Standardized response with college data
    """
    try:
        filters = {}
        result = await explore_service.search_colleges(
            college_names=query.college_name,
            courses=query.course,
            cities=query.city,
            sort_by=query.sort_by,
            order=query.order,
            filters=filters
        )

        # Check if there's an error message in the result
        if "error_message" in result and "error_type" in result:
            error_message = result["error_message"]
            error_type = result["error_type"]
            
            if error_type == "no_results":
                # Raise a LookupError with the specific error message
                raise LookupError(error_message, error_type)
        
        # Check if we have colleges but with course_not_found messages
        has_course_not_found = False
        for college in result.get("colleges", []):
            if college.get("course_not_found", False):
                has_course_not_found = True
                break
        
        # Customize the success message based on results
        success_message = "Colleges retrieved successfully"
        if has_course_not_found:
            success_message = "Colleges found, but some may not offer the requested course"
        elif result.get("total_records", 0) == 0 and query.course:
            success_message = f"No colleges found offering the course: {query.course}"
        
        # Construct successful response
        return ResponseSchema(
            message=success_message,
            success=True,
            data=result
        )

    except LookupError as e:
        error_message = str(e.args[0]) if e.args else "No colleges found"
        error_type = e.args[1] if len(e.args) > 1 else "no_results"
        logging.error(f"Lookup error in search_colleges: {error_message}, type: {error_type}")
        
        # Handle course not found with a specific message
        if error_type == "course_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail={
                    "error": error_message,
                    "technicalError": "Course not found"
                }
            )
        
        # Handle no results found with 404 Not Found
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail={
                "error": error_message,
                "technicalError": "No colleges found"
            }
        )

    except Exception as e:
        logging.error(f"Unexpected error in search_colleges: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail={
                "error": ErrorMessages.ERROR_WHILE_FETCH,
                "technicalError": str(e)
            }
        )

@router.get("/college/{id}", tags=["Colleges"], response_model=ResponseSchema, summary="Get college details by SJ_Institute_Code")
async def get_college_details(
    id: int,
    explore_service: ExploreService = Depends(explore_Service)
):
    """
    Get detailed college info by SJ_Institute_Code, including department meta and cutoff data.
    """
    try:
        college_detail = await explore_service.get_college_report_by_college_name(id)
        data = college_detail
        return ResponseSchema(
            message="College details retrieved successfully",
            success=True,
            data=data
        )
    except Exception as e:
        logging.error(f"Unexpected error in get_college_details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_INTERNAL_SERVER_ERROR, "technicalError": str(e)})

@router.post("/admission-chances",tags=["Admission"], response_model=ResponseSchema, summary="Calculate admission chances")
async def calculate_admission_chances(
    request: AdmissionChancesRequest,
    explore_service: ExploreService = Depends(explore_Service)
):
    """
    Calculate admission chances based on student's CET percentile and college cutoff data.
    
    Parameters:
    - **sj_institute_id**: SJ Institute Code of the college
    - **course_name**: Name of the course/branch
    - **cet_percentile**: Student's CET percentile (0-100)
    - **category**: Category for cutoff (default: GOPENS, options: GOPENS, GSCS, GSTS, GVJS, GNT1S, GNT2S, GNT3S, GOBCS, GSEBCS, LOPENS, LSCS, LSTS, LVJS, LNT1S, LNT2S, LOBCS, LSEBCS, DEFOPENS, DEFOBCS, DEFSEBCS, TFWS, DEFRSEBCS, DEFROBCS, EWS)
    
    Returns:
    - **ResponseSchema**: Standardized response with admission probability data
    """
    try:
        result = await explore_service.calculate_admission_chances(
            sj_institute_id=request.sj_institute_id,
            course_name=request.course_name,
            cet_percentile=request.cet_percentile,
            category=request.category
        )
        
        return ResponseSchema(
            message="Admission chances calculated successfully",
            success=True,
            data=result
        )
        
    except LookupError as e:
        # Handle not found errors (404)
        logging.error(f"Lookup error in calculate_admission_chances: {str(e)}")
        raise HTTPException(status_code=500, detail={"error": str(e), "technicalError": "No colleges found"})
    except ValueError as e:
        # Handle validation errors (400) or data errors (422)
        logging.error(f"Value error in calculate_admission_chances: {str(e)}")
        raise HTTPException(status_code=500, detail={"error": str(e), "technicalError": "No colleges found"})
    except Exception as e:
        # Handle unexpected errors (500)
        logging.error(f"Unexpected error in calculate_admission_chances: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_INTERNAL_SERVER_ERROR, "technicalError": str(e)})

@router.post("/generate_recommendation/", tags=["Recommendation"], summary="Store user recommendation payload as-is")
async def generate_recommendation(
    request: RecommendationRequest,
    recommendation_service: RecommendationService = Depends(recommendation_service)
):
    """
    Store the user recommendation payload as-is in the collection.
    """
    try:
        result = await recommendation_service.generate_recommendation(request)
        return {
            "message": "Recommendation stored successfully.",
            "success": True,
            "data": result
        }
    except ValueError as e:
        logging.error(f"Validation error in generate_recommendation: {str(e)}")
        raise HTTPException(status_code=422, detail={"error": str(e), "technicalError": "Validation error"})
    except Exception as e:
        logging.error(f"Unexpected error in generate_recommendation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_INTERNAL_SERVER_ERROR, "technicalError": str(e)})

@router.get("/fetchAICapDetails", tags=["Recommendation"], dependencies=[Depends(jwtBearer())], summary="Get latest recommendation for the current user", response_model=AICapDetailsResponseSchema)
async def get_my_latest_recommendation(request: Request, recommendation_service: RecommendationService = Depends(recommendation_service)):
    """
    Get the latest recommendation for the current user (by token/email).
    """
    try:
        token = get_token_from_header(request)
        validation_result = validate_google_token(token)
        is_valid = False
        email = None
        if validation_result and isinstance(validation_result, tuple):
            is_valid, email = validation_result
        if not is_valid or not email:
            raise HTTPException(status_code=401, detail={"error": "Invalid or expired token", "technicalError": "Invalid or missing email in token"})
        result = await recommendation_service.get_latest_recommendation_by_email(email)
        if not result:
            return AICapDetailsResponseSchema(
                message="No recommendation found for this user",
                success=True,
                data=None
            )
        return AICapDetailsResponseSchema(
            message="Latest recommendation retrieved successfully",
            success=True,
            data=result
        )
    except Exception as e:
        logging.error(f"Error fetching latest recommendation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_INTERNAL_SERVER_ERROR, "technicalError": str(e)})

@router.get("/colleges/cutoff/all", tags=["Colleges"], response_model=ResponseSchema,dependencies=[Depends(jwtBearer())], summary="Get all cutoff data for all colleges")
async def get_all_colleges_cutoff_data(
    explore_service: ExploreService = Depends(explore_Service)
):
    """
    Get all cutoff data for all colleges, excluding college name from each record.
    """
    try:
        cutoff_data = await explore_service.get_all_cutoff_data()
        return ResponseSchema(
            message="All cutoff data retrieved successfully",
            success=True,
            data=cutoff_data
        )
    except Exception as e:
        logging.error(f"Unexpected error in get_all_colleges_cutoff_data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_INTERNAL_SERVER_ERROR, "technicalError": str(e)})

@router.post("/recommendation/college-list", tags=["Recommendation"],dependencies=[Depends(jwtBearer())], response_model=CollegeRecommendationListResponse, summary="Get recommended colleges grouped by admission chances")
async def get_college_recommendation_list(
    payload:  CollegeRecommendationRequest,
    request: Request,
    explore_service: ExploreService = Depends(explore_Service)
):
    """
    Generate recommended college lists (Dream, Reach, Match, Safety) based on category, courses, percentile, and location.
    
    Request body:
    - Category: str
    - CETCourse: List[str]
    - cet_percentile: float
    - Location: List[str]
    
    Returns:
    - ResponseSchema with Dream, Reach, Match, Safety arrays
    """
    try:
        token = get_token_from_header(request)
        validation_result = validate_google_token(token)
        is_valid = False
        email = None
        if validation_result and isinstance(validation_result, tuple):
            is_valid, email = validation_result
        if not is_valid or not email:
            raise HTTPException(status_code=401, detail={"error": "Invalid or expired token", "technicalError": "Invalid or missing email in token"})
        
        result = await explore_service.generate_college_recommendations(payload, email)
        return CollegeRecommendationListResponse(
            message="College recommendations generated successfully",
            success=True,
            data=result
        )
    except Exception as e:
        logging.error(f"Error generating college recommendations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_INTERNAL_SERVER_ERROR, "technicalError": str(e)})

@router.get("/recommendation/college-list", tags=["Recommendation"],dependencies=[Depends(jwtBearer())], response_model=CollegeRecommendationListResponse, summary="Get recommended colleges grouped by admission chances")
async def get_college_recommendation_list(
    request: Request,
    explore_service: ExploreService = Depends(explore_Service)
):
    """
    Get recommended colleges grouped by admission chances.
    
    Returns:
    - ResponseSchema with Dream, Reach, Match, Safety arrays
    """
    try:
        token = get_token_from_header(request)
        validation_result = validate_google_token(token)
        is_valid = validation_result[0]
        if not is_valid:
            raise HTTPException(status_code=401, detail={"error": "Invalid or expired token", "technicalError": "Invalid or missing email in token"})
        email =validation_result[1]

        result = await explore_service.get_college_recommendation_list(email)
        return CollegeRecommendationListResponse(
            message="College recommendations retrieved successfully",
            success=True,
            data=result
        )
    except Exception as e:
        logging.error(f"Error retrieving college recommendations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_INTERNAL_SERVER_ERROR, "technicalError": str(e)})



@router.post('/generate/round-list', tags=["Recommendation"],dependencies=[Depends(jwtBearer())], response_model=CollegeRecommendationListResponse, summary="Get recommended colleges grouped by admission chances")
async def get_college_recommendation_list_round(
    payload:  CollegeRecommendationRequest,
    request: Request,
    explore_service: ExploreService = Depends(explore_Service)
):
    """
    Get recommended colleges grouped by admission chances.
    
    Returns:
    - ResponseSchema with Dream, Reach, Match, Safety arrays
    """
    try:
        token = get_token_from_header(request)
        validation_result = validate_google_token(token)
        is_valid = validation_result[0]
        if not is_valid:
            raise HTTPException(status_code=401, detail={"error": "Invalid or expired token", "technicalError": "Invalid or missing email in token"})
        email =validation_result[1]
        result = await explore_service.generate_college_recommendations_round(payload, email)
        return CollegeRecommendationListResponse(
            message="College recommendations generated successfully",
            success=True,
            data=result
        )
    except Exception as e:
        logging.error(f"Error generating college recommendations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_INTERNAL_SERVER_ERROR, "technicalError": str(e)})



@router.post('/search_college_by/choice_code', tags=["Recommendation"],dependencies=[Depends(jwtBearer())], response_model=dict, summary="Get recommended colleges grouped by admission chances")
async def search_college_by_choice_code(
    payload:  SearchByChoiceCode,
    request: Request,
    explore_service: ExploreService = Depends(explore_Service)
):
    """
    Get recommended colleges grouped by admission chances.
    
    Returns:
    - ResponseSchema with Dream, Reach, Match, Safety arrays
    """
    try:
        token = get_token_from_header(request)
        validation_result = validate_google_token(token)
        is_valid = validation_result[0]
        if not is_valid:
            raise HTTPException(status_code=401, detail={"error": "Invalid or expired token", "technicalError": "Invalid or missing email in token"})
        email =validation_result[1]
        result = await explore_service.search_college_by_choice_code(payload, email)
        return {
            "message":"College recommendations retrieved successfully",
            "success":True,
            "data":result
        }
    except Exception as e:
        logging.error(f"Error retrieving college recommendations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_INTERNAL_SERVER_ERROR, "technicalError": str(e)})

@router.post('/search_college_by/college_name', tags=["Recommendation"],dependencies=[Depends(jwtBearer())], response_model=dict, summary="Get recommended colleges grouped by admission chances")
async def search_college_by_college_name(
    payload:  SearchByCollegeName,
    request: Request,
    explore_service: ExploreService = Depends(explore_Service)
):
    """
    Get recommended colleges grouped by admission chances.
    
    Returns:
    - ResponseSchema with Dream, Reach, Match, Safety arrays
    """
    try:
        token = get_token_from_header(request)
        validation_result = validate_google_token(token)
        is_valid = validation_result[0]
        if not is_valid:
            raise HTTPException(status_code=401, detail={"error": "Invalid or expired token", "technicalError": "Invalid or missing email in token"})
        result = await explore_service.search_college_by_college_name(payload)
        return {
            "message":"College recommendations retrieved successfully",
            "success":True,
            "data":result
        }
    except Exception as e:
        logging.error(f"Error retrieving college recommendations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_INTERNAL_SERVER_ERROR, "technicalError": str(e)}) 

@router.post('/search_college_by/college_code', tags=["Recommendation"],dependencies=[Depends(jwtBearer())], response_model=dict, summary="Get recommended colleges grouped by admission chances")
async def search_college_by_college_code(
    payload:  SearchByCollegeCode,
    request: Request,
    explore_service: ExploreService = Depends(explore_Service)
):
    """
    Get recommended colleges grouped by admission chances.
    
    Returns:
    - ResponseSchema with Dream, Reach, Match, Safety arrays
    """
    try:
        token = get_token_from_header(request)
        validation_result = validate_google_token(token)
        is_valid = validation_result[0]
        if not is_valid:
            raise HTTPException(status_code=401, detail={"error": "Invalid or expired token", "technicalError": "Invalid or missing email in token"})
        email =validation_result[1]
        result = await explore_service.search_college_by_college_code(payload)
        return {
            "message":"College recommendations retrieved successfully",
            "success":True,
            "data":result
        }
    except Exception as e:
        logging.error(f"Error retrieving college recommendations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_INTERNAL_SERVER_ERROR, "technicalError": str(e)}) 




@router.post('/generate/diploma-round-list', tags=["Diploma"],dependencies=[Depends(jwtBearer())], response_model=dict, summary="Get recommended colleges grouped by admission chances")
async def get_college_recommendation_list_diploma(
    payload:  CollegeRecommendationRequest,
    request: Request,
    explore_service: ExploreService = Depends(explore_Service)
):
    """
    Get recommended colleges grouped by admission chances.
    
    Returns:
    - ResponseSchema with Dream, Reach, Match, Safety arrays
    """
    try:
        token = get_token_from_header(request)
        validation_result = validate_google_token(token)
        is_valid = validation_result[0]
        if not is_valid:
            raise HTTPException(status_code=401, detail={"error": "Invalid or expired token", "technicalError": "Invalid or missing email in token"})
        email =validation_result[1]
        result = await explore_service.generate_college_recommendations_diploma(payload, email)
        return {
            "message":"College recommendations generated successfully",
            "success":True,
            "data":result
        }
    except Exception as e:
        logging.error(f"Error generating college recommendations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_INTERNAL_SERVER_ERROR, "technicalError": str(e)})


@router.get("/get/diploma-round-list/{round_no}", tags=["Diploma"],dependencies=[Depends(jwtBearer())], response_model=dict, summary="Get recommended colleges grouped by admission chances")
async def get_college_recommendation_list_diploma(
    request: Request,
    round_no: int,
    explore_service: ExploreService = Depends(explore_Service)
):
    """
    Get recommended colleges grouped by admission chances.
    
    Returns:
    - ResponseSchema with Dream, Reach, Match, Safety arrays
    """
    try:
        token = get_token_from_header(request)
        validation_result = validate_google_token(token)
        is_valid = validation_result[0]
        if not is_valid:
            raise HTTPException(status_code=401, detail={"error": "Invalid or expired token", "technicalError": "Invalid or missing email in token"})
        email =validation_result[1]
        result = await explore_service.get_college_recommendation_list_diploma(round_no, email)
        return {
            "message":"College recommendations retrieved successfully",
            "success":True,
            "data":result
        }
    except Exception as e:
        logging.error(f"Error retrieving college recommendations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_INTERNAL_SERVER_ERROR, "technicalError": str(e)})

@router.get('/get-diploma-config/{round_no}', tags=["Diploma"],dependencies=[Depends(jwtBearer())], response_model=dict, summary="Get recommended colleges grouped by admission chances")
async def get_diploma_config(
    request: Request,
    round_no: int,  
    explore_service: ExploreService = Depends(explore_Service)
):
    """
    Get recommended colleges grouped by admission chances.
    
    Returns:
    - ResponseSchema with Dream, Reach, Match, Safety arrays
    """
    try:
        token = get_token_from_header(request)
        validation_result = validate_google_token(token)
        is_valid = validation_result[0]
        if not is_valid:
            raise HTTPException(status_code=401, detail={"error": "Invalid or expired token", "technicalError": "Invalid or missing email in token"})
        email =validation_result[1]
        result = await explore_service.get_diploma_config(round_no, email)
        return {
            "message":"College recommendations retrieved successfully", 
            "success":True,
            "data":result
        }
    except Exception as e:
        logging.error(f"Error retrieving college recommendations: {str(e)}", exc_info=True) 
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_INTERNAL_SERVER_ERROR, "technicalError": str(e)})


