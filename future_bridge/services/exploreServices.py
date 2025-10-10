from calendar import c
from fastapi import HTTPException
from typing import Optional, List, Dict, Any, Union, cast
import logging
import math
from future_bridge.api.v1.userRouters import store_user
from future_bridge.repositories.exploreRepository import ExploreRepository
from future_bridge.schema.instituteSchema import CollegeSummaryResponse, PlacementRange, CETCutoffRange, CollegeDetailResponse, InstituteMeta, DepartmentMeta, CutoffMeta, CourseCutoffGroup
from future_bridge.schema.recommendationSchema import CollegeRecommendationGroupResponse, CollegeRecommendationRequest
from future_bridge.utils.db import get_db
from future_bridge.config.config import settings
from future_bridge.repositories.paymentRepository import PaymentRepository
from future_bridge.repositories.recommendationRepository import RecommendationRepository
from future_bridge.schema.recommendationSchema import SearchByChoiceCode , SearchByCollegeName ,SearchByCollegeCode


class ExploreService:

    def __init__(self):
        self.explore_repository = ExploreRepository()
        self.payment_repository = PaymentRepository()
        self.recommendation_repository = RecommendationRepository()
    def _safe_float(self, val):
        if val is None:
            return None
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return None
            return f
        except Exception:
            return None

    async def search_colleges(self, college_names: Optional[List[str]] = None, courses: Optional[List[str]] = None, cities: Optional[List[str]] = None, sort_by: Optional[str] = None, order: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Searches for colleges and returns a structured response with data and filtering options. Supports multiple cities, colleges, and courses.
        """
        logging.info('Searching for colleges with provided filters')
        
        try:
            result = await self.explore_repository.search_colleges(
                college_names=college_names,
                courses=courses,
                cities=cities,
                sort_by=sort_by,
                order=order,
                filters=filters
            )

            colleges = result.get("colleges", [])
            cities = result.get("cities", [])
            total_records = result.get("total_records", 0)
            error_message = result.get("error_message")
            error_type = result.get("error_type")

            # The repository layer now raises exceptions directly, so we don't need to check for empty colleges here
            # This block is kept for backward compatibility in case the repository returns empty results without raising an exception
            if not colleges:
                logging.warning("No colleges found for search criteria.")
                # Generic error message
                raise LookupError("No colleges found for the specified search criteria.", "no_results")

            # Format college data for response
            colleges_data = []
            for college in colleges:
                # Extract courses from departments first to ensure accurate count
                courses = []
                if "departments" in college and college["departments"]:
                    for dept in college["departments"]:
                        if "Common_Name" in dept and dept["Common_Name"]:
                            # Split by comma if multiple courses are in one string
                            if isinstance(dept["Common_Name"], str):
                                course_list = [c.strip() for c in dept["Common_Name"].split(",")]
                                courses.extend(course_list)
                            else:
                                courses.append(str(dept["Common_Name"]))
                unique_courses = list(set(courses))

                """
                The city field in the response should be the region, not the city.
                This is because the city field is used to filter the results, and the region field is used to display the results.
                """
                college_summary = {
                    "college_name": college.get("College_Name", ""),
                    "college_type": college.get("College_Type", ""),
                    "institute_id": college.get("College_Code", ""),
                    "sj_institute_id" : college.get("SJ_Institute_Code", ""),
                    "city":college.get('Region',None),
                    "Region": college.get("City", ""),
                    "logo": college.get("College_Logo", ""),
                    "rating": college.get("College_Reviews_out_of_5", 0),
                    "courses_count": len(unique_courses),
                    "total_intake": college.get("Student_Intake", college.get("Total_Intake", None)),
                    "fees": college.get("Annual_Fees_INR", college.get("Annual_Fees_(INR)", None)),
                    "placement_range": self._get_placement_range(college),
                    "cet_cutoff_range": self._get_cutoff_range(college)
                }
                if unique_courses:
                    college_summary["courses"] = unique_courses
                if college.get("course_not_found") and college.get("course_not_found_message"):
                    college_summary["course_not_found"] = True
                    college_summary["course_not_found_message"] = college.get("course_not_found_message")
                colleges_data.append(college_summary)

            return {
                "colleges": colleges_data,
                "cities": cities,
                "total_records": total_records
            }

        except LookupError as e:
            logging.error(f"Lookup error in search_colleges: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in search_colleges: {str(e)}", exc_info=True)
            raise Exception(f"Failed to search colleges: {str(e)}")
    
    def _get_placement_range(self, college: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """Helper method to extract placement range from college data"""
        placement_min = None
        placement_max = None
        placement_percentages = []

        # Get placement percentages from departments if present and not empty
        departments = college.get("departments")
        if departments and isinstance(departments, list):
            for dept in departments:
                val = dept.get("Placement_Percentage")
                if val is not None:
                    try:
                        if isinstance(val, (int, float)):
                            float_val = float(val)
                            if not math.isnan(float_val) and not math.isinf(float_val):
                                placement_percentages.append(float_val)
                        else:
                            numeric_val = float(str(val).replace('%', '').replace(',', ''))
                            if not math.isnan(numeric_val) and not math.isinf(numeric_val):
                                placement_percentages.append(numeric_val)
                    except (ValueError, TypeError, OverflowError):
                        pass
            if placement_percentages:
                if len(placement_percentages) == 1:
                    placement_min = 0
                    placement_max = placement_percentages[0]
                else:
                    placement_min = min(placement_percentages)
                    placement_max = max(placement_percentages)

        # Fallback: If no valid department data, use Overall_College_Placement_Percentage
        if not placement_percentages:
            placement_field = college.get("Overall_College_Placement_Percentage")
            if placement_field is not None:
                try:
                    placement_max = float(placement_field)
                    if math.isnan(placement_max) or math.isinf(placement_max):
                        placement_max = None
                    else:
                        placement_min = 0
                except (ValueError, TypeError, OverflowError):
                    placement_max = None

        return {
            "min": self._safe_float(placement_min),
            "max": self._safe_float(placement_max)
        }
    
    def _get_cutoff_range(self, college: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """Helper method to extract CET cutoff range from college data. Now only returns max as the latest CET cutoff for GOPENS, min is always None."""
        cutoff_max = None
        # Use the new field from the repo result
        if "latest_cet_cutoff_max" in college:
            cutoff_max = self._safe_float(college["latest_cet_cutoff_max"])
            if cutoff_max is not None:
                cutoff_max = round(cutoff_max, 2)
        if "latest_cet_cutoff_min" in college:
            cutoff_min = self._safe_float(college["latest_cet_cutoff_min"])
            if cutoff_min is not None:
                cutoff_min = round(cutoff_min, 2)
        
        return {"min": cutoff_min, "max": cutoff_max}

    async def get_college_details_by_sj_code(self, sj_code: int) -> dict:
        """
        Fetch all data for institute_meta using SJ_Institute_Code.
        Returns the full document with {'_id': 0}.
        """
        try:
            result = await self.explore_repository.get_institute_meta_by_sj_code(sj_code)
            return result
        except Exception as e:
            import logging
            logging.error(f"Error fetching institute_meta by SJ_Institute_Code: {e}")
            raise

    async def get_departments_by_college_name(self, sj_code: int) -> list:
        """
        Fetch all department_meta documents for a given college name.
        """
        try:
            return await self.explore_repository.get_departments_by_college_name(sj_code)
        except Exception as e:
            import logging
            logging.error(f"Error fetching department_meta by SJ_Institute_Code: {e}")
            raise

    async def calculate_admission_chances(self, sj_institute_id: int, course_name: str, cet_percentile: float, category: str = "GOPENS") -> dict:
        """
        Calculate admission chances based on student's CET percentile and college cutoff data for a specific category.
        """
        try:          
            # Get cutoff data for the college, course, and category
            cutoff_data = await self.explore_repository.get_cutoff_data_for_admission_chances(sj_institute_id, course_name, category)
            last_year_cutoff = cutoff_data["cutoff_value"]
            cutoff_year = cutoff_data["year"]
            cutoff_category = cutoff_data["category"]
            
            # Calculate the difference between student's percentile and cutoff
            percentile_diff = cet_percentile - last_year_cutoff
            
            # Calculate admission probability based on the formula
            admission_probability, probability_message = self._calculate_probability(percentile_diff, cet_percentile)
            
            return {
                "college_name": cutoff_data.get("college_name"),
                "course_name": course_name,
                "category": cutoff_category,
                "student_cet_percentile": cet_percentile,
                "last_year_cutoff": last_year_cutoff,
                "cutoff_year": cutoff_year,
                "admission_probability": admission_probability,
                "probability_message": probability_message
            }
            
        except (LookupError, ValueError):
            # Re-raise these exceptions as they are already properly formatted
            raise
        except Exception as e:
            logging.error(f"Error calculating admission chances: {e}")
            raise Exception(f"Service error while calculating admission chances: {str(e)}")

    def _calculate_probability(self, percentile_diff: float, cet_percentile: Optional[float] = None) -> tuple[int, str]:
        """
        Calculate admission probability based on the difference between student's CET percentile and cutoff.
        Returns (probability_percentage, message)
        If cet_percentile is 100, always return 99%.
        """
        if cet_percentile is not None and cet_percentile == 100:
            return 99, "Excellent chances - You have the highest possible percentile (100%)"
        if percentile_diff >= 4:
            return 99, "Excellent chances - Your score is significantly above the cutoff (4+ points above)"
        elif 3 <= percentile_diff < 4:
            return 95, "Very high chances - Your score is 3 to 4 points above the cutoff"
        elif 2 <= percentile_diff < 3:
            return 90, "High chances - Your score is 2 to 3 points above the cutoff"
        elif 1 <= percentile_diff < 2:
            return 85, "Good chances - Your score is 1 to 2 points above the cutoff"
        elif 0.5 <= percentile_diff < 1:
            return 80, "Fair chances - Your score is 0.5 to 1 point above the cutoff"
        elif 0 < percentile_diff < 0.5:
            return 75, "Moderate chances - Your score is up to 0.5 points above the cutoff"
        elif 0 > percentile_diff >= -0.5:
            return 70, "Low-moderate chances - Your score is up to 0.5 points below the cutoff"
        elif -0.5 > percentile_diff >= -1:
            return 65, "Low chances - Your score is 0.5 to 1 point below the cutoff"
        elif -1 > percentile_diff >= -2:
            return 60, "Very low chances - Your score is 1 to 2 points below the cutoff"
        elif -2 > percentile_diff >= -3:
            return 50, "Minimal chances - Your score is 2 to 3 points below the cutoff"
        elif -3 > percentile_diff >= -4:
            return 40, "Very minimal chances - Your score is 3 to 4 points below the cutoff"
        elif -4 > percentile_diff >= -5:
            return 30, "Extremely low chances - Your score is 4 to 5 points below the cutoff"
        elif -5 > percentile_diff >= -10:
            return 20, "Extremely low chances - Your score is 5 to 10 points below the cutoff"
        else:
            return 10, "Extremely low chances - Your score is more than 10 points below the cutoff"

    async def get_college_report_by_college_name(self, id: int) -> dict:
        """
        Generate a detailed college report by college_name, including meta, departments, and cutoffs.
        The response merges all institute_meta fields at the top level, along with custom blocks.
        """
        try:
            # Fetch meta
            meta = await self.explore_repository.get_institute_meta_by_sj_code(id)
            if not meta:
                raise LookupError(f"No college found with id: {id}")

            # Fetch departments
            departments = await self.explore_repository.get_departments_by_college_name(id)

            # Build Departments list as per schema
            departments_out = []
            placement_percentages = []
            for dept in departments:
                course_name = dept.get("Courses_Offered")
                # Fetch latest cutoff for this course (always a dict or None)
                cut_cet = await self.explore_repository.get_cutoff_by_college_name_and_course(id, course_name)
                # CET block
                gopens_cutoff = None
                if cut_cet:
                    gopens_cutoff = cut_cet.get("GOPENS")
                    if gopens_cutoff is not None:
                        gopens_cutoff = round(float(gopens_cutoff), 2)
                dept_out = {
                    "Department_Name": course_name,
                    "NBA_Accredited": dept.get("NBA_Accredited", "No"),
                    "Placement_Percentage": dept.get("Placement_Percentage"),
                    "Student_Intake": dept.get("Student_Intake"),
                    "CET": gopens_cutoff,
                    "JEE": None,
                    "Other Entrance" : None
                }
                departments_out.append(dept_out)

            # Facilities block
            facilities = {
                "Hostel": meta.get("College_Hostel_Available", "No"),
                "Lab": meta.get("Lab_Facilities"),
                "Sports": meta.get("Sports_Facilities"),
                "Bus": meta.get("College_Bus_Facility_Available", "No"),
                "Internet": "Yes" if meta.get("Lab_Facilities") else "No"
            }
            # Placement block
            placement_details = {
                "Overall_College_Placement_Percentage": meta.get("Overall_College_Placement_Percentage"),
                "Highest_Package_LPA": meta.get("Previous_Year_Highest_Package_Offered_LPA"),
                "Average_Package_LPA": None,
                "Top_Recruiters": meta.get("Top_Recruiters")
            }
            # Location block
            location = {
                "Address": meta.get("College_Address"),
                "City": meta.get("City"),
                "Nearest_Railway_Station": meta.get("Nearest_Railway_Station"),
                "Distance_from_Railway_Station_km": meta.get("Distance_from_Railway_Station"),
                "Nearest_Airport": meta.get("Nearest_Airport"),
                "Distance_from_Airport_km": meta.get("Distance_from_Airport")
            }
            # Compose final response: merge all meta fields at top level, then add custom blocks
            response = {
                "College_Name": meta.get("College_Name"),
                "College_Website": meta.get("College_Website"),
                "College_Address": meta.get("College_Address"),
                "City": meta.get("City"),
                "College_Type": meta.get("College_Type"),
                "NAAC_Acrredition": meta.get("NAAC_Acrredition"),
                "University_Affiliation": meta.get("University_Affiliation"),
                "Annual_Fees_(INR)": meta.get("Annual_Fees_(INR)"),
                "Previous_Year_Highest_Package_Offered_(LPA)": meta.get("Previous_Year_Highest_Package_Offered_(LPA)"),
                "Student_Intake": meta.get("Student_Intake"),
                "College_Reviews_out_of_5": meta.get("College_Reviews_out_of_5"),
                "Faculty_Student_Ratio": meta.get("Faculty_Student_Ratio"),
                "NIRF_Rank_Min": meta.get("NIRF_Rank_Min"),
                "NIRF_Rank_Max": meta.get("NIRF_Rank_Max"),
                "College_Code": meta.get("College_Code"),
                "Average_Placement_Percentage": None,
                "SJ_Institute_Code": meta.get("SJ_Institute_Code"),
                "College_Logo": meta.get("College_Logo"),
                "Engineering_Streams": len(departments_out),
                "Established_Year": meta.get("Established_Year", None),
                "Facilities": facilities,
                "Placement_Details": placement_details,
                "Admission_Process": "Merit based on MHT-CET, JEE Main",
                "Location": location,
                "Departments": departments_out
            }
            return response
        except Exception as e:
            logging.error(f"Error generating college report for {id}: {e}")
            raise


    async def get_all_cutoff_data(self) -> list[dict]:
        """
        Fetch all cutoff data for all colleges, returning a list of dicts (excluding college name).
        """
        try:
            return await self.explore_repository.get_all_cutoff_data()
            

        except Exception as e:
            logging.error(f"Error in service while fetching all cutoff data: {e}")
            raise

    async def generate_college_recommendations(self, payload: CollegeRecommendationRequest, email: str) -> CollegeRecommendationGroupResponse:
        """
        Generate college recommendations based on category, courses, percentile, and location.
        Returns grouped arrays: Dream, Reach, Match, Safety.
        """
        category = payload.category
        courses = payload.cet_course
        cet_percentile = payload.cet_percentile
        locations = payload.location

        if not category or cet_percentile is None or not courses:
            return CollegeRecommendationGroupResponse(
                Dream=[],
                Reach=[],
                Match=[],
                Safety=[],
                is_payment=False,
                accept_payment=False
            )
        
        # Set default values for is_payment and accept_payment
        is_payment = False
        accept_payment = False
        # Fetch cutoff data (no location filtering here)
        cutoff_data = await self.explore_repository.get_cutoff_by_category_course_location(str(category), courses,locations)
        results = []
        is_payment = await self.payment_repository.is_user_payment_successful(email)
        accept_payment = await self.payment_repository.get_accept_payment_from_config() 
        for doc in cutoff_data:
            try:
                sj_code = doc.get("SJ_Institute_Code")
                course_name = doc.get("Course_Name")
                cutoff_val = doc.get(category)
                if sj_code is None or cutoff_val is None:
                    continue
                try:
                    last_year_cutoff = float(cutoff_val)
                except Exception:
                    continue
                try:
                    sj_code_int = int(sj_code)
                except Exception:
                    continue
                percentile_diff = cet_percentile - last_year_cutoff
                admission_probability, probability_message = self._calculate_probability(percentile_diff, cet_percentile)
                # Fetch college meta with optional location filtering
                meta = await self.explore_repository.get_institute_meta_by_sj_code(sj_code_int, locations)

                result = {
                    "college": meta,
                    "course": course_name,
                    "admission_probability": admission_probability,
                    "probability_message": probability_message,
                    "cet_percentile": cet_percentile,
                    "category": category,
                    "cutoff": round(float(last_year_cutoff), 2)
                }
                results.append(result)
            except Exception as e:
                continue
        # Grouping logic
        dream_all = sorted([r for r in results if 20 <= r["admission_probability"] < 50], key=lambda x: -x["cutoff"])
        reach_all = sorted([r for r in results if 50 <= r["admission_probability"] < 75], key=lambda x: -x["cutoff"])
        match_all = sorted([r for r in results if 75 <= r["admission_probability"] < 90], key=lambda x: -x["cutoff"])
        safety_all = sorted([r for r in results if r["admission_probability"] >= 90], key=lambda x: -x["cutoff"])

        # match_all.sort(key=lambda x: x["cutoff"])
        # Step 2: Fill Match and get overflow
        match = match_all[:50]
        match_overflow = match_all[50:]

        # Step 3: Add match overflow to reach
        reach_all += match_overflow
        reach = reach_all[:15]
        reach_overflow = reach_all[15:]

        # Step 4: Add reach overflow to dream
        dream_all += reach_overflow
        dream = dream_all[:5]

        # Step 5: Safety will include original safety list + dream_overflow
        # Total items so far
        used = len(match) + len(reach) + len(dream)
        remaining_slots = 300 - used

        # Add as many from safety_all + dream_overflow as possible
        combined_safety_pool = safety_all
        safety = combined_safety_pool[:remaining_slots]
        college_recommendation = CollegeRecommendationGroupResponse(
            username=email,
            Dream=dream,
            Reach=reach,
            Match=match,
            Safety=safety,
            is_payment=is_payment,
            accept_payment=accept_payment
        )
        await self.recommendation_repository.store_college_recommendations(college_recommendation)   
        return college_recommendation

    async def generate_college_recommendations_round(self, payload: CollegeRecommendationRequest, email: str) -> CollegeRecommendationGroupResponse:
        """
        Generate college recommendations for round 2 based on the previous round's choice.
        """
        category = payload.category
        last_round_college_choice_code = payload.last_round_college_choice_code
        cet_percentile = payload.cet_percentile
        cet_courses = payload.cet_course
        location = payload.location
        round_no = payload.round
        is_payment = await self.payment_repository.is_user_payment_successful(email)
        accept_payment = await self.payment_repository.get_accept_payment_from_config() 
        if not category or cet_percentile is None or not cet_courses or last_round_college_choice_code is None:
            return CollegeRecommendationGroupResponse(
                Dream=[],
                Reach=[],
                Match=[],
                Safety=[],
                is_payment=False,
                accept_payment=False
            )
        if last_round_college_choice_code ==0:
            cet_cutoff_data = await self.explore_repository.get_cutoff_by_category_course_location(str(category), cet_courses,location,round_no=round_no)
        else:
            get_previous_year_round_cutoff = await self.explore_repository.get_previous_year_round_cutoff(last_round_college_choice_code,category,round_no)

            last_year_round_cutoff = get_previous_year_round_cutoff.get("last_year_cutoff")
            cet_cutoff_data = await self.explore_repository.get_courses_cutoff(cet_courses,round_no,last_year_round_cutoff,category,location)
        # meta = await self.explore_repository.get_institute_meta_by_sj_code(sj_code_int, locations)
        results = []

        for doc in cet_cutoff_data:
            try:
                sj_code = doc.get("SJ_Institute_Code")
                course_name = doc.get("Course_Name")
                cutoff_val = doc.get(category)
                if sj_code is None or cutoff_val is None:
                    continue
                try:
                    last_year_cutoff = float(cutoff_val)
                except Exception:
                    continue
                try:
                    sj_code_int = int(sj_code)
                except Exception:
                    continue
                percentile_diff = cet_percentile - last_year_cutoff
                admission_probability, probability_message = self._calculate_probability(percentile_diff, cet_percentile)
                # Fetch college meta with optional location filtering
                meta = await self.explore_repository.get_institute_meta_by_sj_code(sj_code_int, location)

                result = {
                    "college": meta,
                    "course": course_name,
                    "admission_probability": admission_probability,
                    "probability_message": probability_message,
                    "cet_percentile": cet_percentile,
                    "category": category,
                    "cutoff": round(float(last_year_cutoff),2)
                }
                results.append(result)
            except Exception as e:
                continue

        dream_all = sorted([r for r in results if 20 <= r["admission_probability"] < 50], key=lambda x: -x["cutoff"])
        reach_all = sorted([r for r in results if 50 <= r["admission_probability"] < 75], key=lambda x: -x["cutoff"])
        match_all = sorted([r for r in results if 75 <= r["admission_probability"] < 90], key=lambda x: -x["cutoff"])
        safety_all = sorted([r for r in results if r["admission_probability"] >= 90], key=lambda x: -x["cutoff"])

        # Step 2: Fill Match and get overflow
        match = match_all[:50]
        match_overflow = match_all[50:]

        # Step 3: Add match overflow to reach
        reach_all += match_overflow
        reach = reach_all[:25]
        reach_overflow = reach_all[25:]

        # Step 4: Add reach overflow to dream
        dream_all += reach_overflow
        dream = dream_all[:10]

        # Step 5: Safety will include original safety list + dream_overflow
        # Total items so far
        used = len(match) + len(reach) + len(dream)
        remaining_slots = 300 - used

        # Add as many from safety_all + dream_overflow as possible
        combined_safety_pool = safety_all
        safety = combined_safety_pool[:remaining_slots]
        college_recommendation = CollegeRecommendationGroupResponse(
            Round=round_no,
            username=email,
            Dream=dream,
            Reach=reach,
            Match=match,
            Safety=safety,
            is_payment=is_payment,
            accept_payment=accept_payment
        )
        await self.recommendation_repository.store_college_recommendations(college_recommendation,round_no)   
        return college_recommendation

    async def generate_college_recommendations_diploma(self, payload: CollegeRecommendationRequest, email: str) -> CollegeRecommendationGroupResponse:
        """
        Generate college recommendations for diploma based on the previous round's choice.
        """
        category = payload.category
        last_round_college_choice_code = payload.last_round_college_choice_code
        cet_percentile = payload.cet_percentile
        cet_courses = payload.cet_course
        location = payload.location
        round_no = payload.round
        await self.explore_repository.store_diploma_user_config(payload,email)
        is_payment = await self.payment_repository.is_user_payment_successful(email,diploma=True)
        accept_payment = await self.payment_repository.get_accept_payment_from_config() 
        if last_round_college_choice_code is None and round_no !=1:

            return CollegeRecommendationGroupResponse(
                username=email,
                round_no=round_no,
                Dream=[],
                Reach=[],
                Match=[],
                Safety=[],
                is_payment=False,
                accept_payment=False
            )
        if not category or cet_percentile is None or not cet_courses:
            return CollegeRecommendationGroupResponse(
                username=email,
                round_no=round_no,
                Dream=[],
                Reach=[],
                Match=[],
                Safety=[],
                is_payment=False,
                accept_payment=False
            )
        if round_no >1 and last_round_college_choice_code !=0:

            get_previous_year_round_cutoff = await self.explore_repository.get_previous_year_round_cutoff(last_round_college_choice_code,category,round_no,diploma=True)

            
            last_year_round_cutoff = get_previous_year_round_cutoff.get("last_year_cutoff")

            cet_cutoff_data = await self.explore_repository.get_courses_cutoff(cet_courses,round_no,last_year_round_cutoff,category,location,diploma=True)

        else:
            cet_cutoff_data = await self.explore_repository.get_cutoff_by_category_course_location(str(category), cet_courses,location,round_no=round_no,diploma=True)
        results = []
        for doc in cet_cutoff_data:
            try:
                sj_code = doc.get("SJ_Institute_Code")
                course_name = doc.get("Course_Name")
                cutoff_val = doc.get(category)
                if sj_code is None or cutoff_val is None:
                    continue
                try:
                    last_year_cutoff = float(cutoff_val)
                except Exception:
                    continue
                try:
                    sj_code_int = int(sj_code)
                except Exception:
                    continue
                percentile_diff = cet_percentile - last_year_cutoff
                admission_probability, probability_message = self._calculate_probability(percentile_diff, cet_percentile)
                # Fetch college meta with optional location filtering
                meta = await self.explore_repository.get_institute_meta_by_sj_code(sj_code_int, location)

                result = {
                    "college": meta,
                    "course": course_name,
                    "admission_probability": admission_probability,
                    "probability_message": probability_message,
                    "cet_percentile": cet_percentile,
                    "category": category,
                    "cutoff": round(float(last_year_cutoff),2)
                }
                results.append(result)
            except Exception as e:
                continue
                
        dream_all = sorted([r for r in results if 20 <= r["admission_probability"] < 50], key=lambda x: -x["cutoff"])
        reach_all = sorted([r for r in results if 50 <= r["admission_probability"] < 75], key=lambda x: -x["cutoff"])
        match_all = sorted([r for r in results if 75 <= r["admission_probability"] < 90], key=lambda x: -x["cutoff"])
        safety_all = sorted([r for r in results if r["admission_probability"] >= 90], key=lambda x: -x["cutoff"])

        # Step 2: Fill Match and get overflow
        match = match_all[:50]
        match_overflow = match_all[50:]

        # Step 3: Add match overflow to reach
        reach_all += match_overflow
        reach = reach_all[:25]
        reach_overflow = reach_all[25:]

        # Step 4: Add reach overflow to dream
        dream_all += reach_overflow
        dream = dream_all[:15]

        # Step 5: Safety will include original safety list + dream_overflow
        # Total items so far
        used = len(match) + len(reach) + len(dream)
        remaining_slots = 300 - used

        # Add as many from safety_all + dream_overflow as possible
        combined_safety_pool = safety_all
        safety = combined_safety_pool[:remaining_slots]
        college_recommendation = CollegeRecommendationGroupResponse(
            Round=round_no,
            username=email,
            Dream=dream,
            Reach=reach,
            Match=match,
            Safety=safety,
            is_payment=is_payment,
            accept_payment=accept_payment
        )
        await self.recommendation_repository.store_college_recommendations(college_recommendation,round_no,diploma=True)   

        return college_recommendation    
    
    async def get_college_recommendation_list_diploma(self, round_no: int, email: str) -> CollegeRecommendationGroupResponse:
        """
        Fetch college recommendations for a user by email.
        """
        try:
            is_payment = await self.payment_repository.is_user_payment_successful(email)

            response = await self.recommendation_repository.get_college_recommendations_by_email(email,round_no,diploma=True)
            response.is_payment = is_payment
            return response
        except Exception as e:
            logging.error(f"Error in service while fetching college recommendations: {e}")
            raise

    async def get_diploma_config(self, round_no: int, email: str) -> dict:
        """
        Fetch diploma config for a user by email.
        """
        try:
            response = await self.explore_repository.get_diploma_user_config(email,round_no)

            return response
        except Exception as e:
            logging.error(f"Error in service while fetching diploma config: {e}")
            raise
        
    async def search_college_by_college_code(self, payload: SearchByCollegeCode) -> List[dict]:
        """
        Search for colleges by college code.
        """
        try:
            college_code = payload.college_code
            result = await self.explore_repository.search_college_by_college_code(college_code)
            return result
        except Exception as e:
            logging.error(f"Error in service while searching college by code: {e}")
            raise
    
    async def search_college_by_college_name(self, payload: SearchByCollegeName) -> List[dict]:
        """
        Search for colleges by college name.
        """
        try:
            college_name = payload.college_name
            result = await self.explore_repository.search_college_by_college_name(college_name)
            return result
        except Exception as e:
            logging.error(f"Error in service while searching college by name: {e}")
            raise
    async def search_college_by_choice_code(self, payload: SearchByChoiceCode,email: str) -> List[dict]:
        """
        Search for colleges by choice code.
        """
        try:
            choice_code = payload.choice_code
            result = await self.explore_repository.search_college_by_choice_code(choice_code,email)
            return result
        except Exception as e:
            logging.error(f"Error in service while searching college by code: {e}")
            raise

    async def get_college_recommendation_list(self, email: str) -> CollegeRecommendationGroupResponse:
        """
        Fetch college recommendations for a user by email.
        """
        try:
            is_payment = await self.payment_repository.is_user_payment_successful(email)

            response = await self.recommendation_repository.get_college_recommendations_by_email(email)
            response.is_payment = is_payment
            return response
        except Exception as e:
            logging.error(f"Error in service while fetching college recommendations: {e}")
            raise

def explore_Service() -> ExploreService:
    return ExploreService()
