from os import curdir
from future_bridge.utils.db import get_db
from future_bridge.config.config import settings
import logging
import re
from bson import ObjectId
import math  # Ensure math is imported for isnan and isinf functions
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, List, Optional, Any, final
from future_bridge.models.userModel import DiplomaUserConfig

class ExploreRepository:

    async def search_colleges(self, college_names: Optional[List[str]] = None, courses: Optional[List[str]] = None, cities: Optional[List[str]] = None, sort_by: Optional[str] = None, order: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Searches for colleges based on search parameters and additional filters, supports multiple cities, colleges, and courses.
        Returns only the highest GOPENS CET cutoff for the latest year for each college.
        """
        try:
            db = await get_db()
            institute_collection = db[settings.INSTIUTE_META_COLLECTION]
            department_collection = db[settings.DEPARTMENT_META_COLLECTION]
            cutoff_collection = db[settings.COLLEGE_CUTOFF_COLLECTION]
            
            # Build query conditions
            query_conditions = []
            if college_names:
                query_conditions.append({
                    "$or": [
                        {"College_Name": {"$regex": name, "$options": "i"}}
                        for name in college_names
                    ]
                })
            if cities:
                query_conditions.append({
                    "$or": [
                        {"City": {"$regex": city, "$options": "i"}}
                        for city in cities
                    ]
                })
            if filters:
                if isinstance(filters, dict) and not any(key.startswith('$') for key in filters):
                    for key, value in filters.items():
                        query_conditions.append({key: value})
                else:
                    query_conditions.append(filters)
            
            # Handle course filtering
            if courses:
                course_query = {"$or": [{"Courses_Offered": {"$regex": course, "$options": "i"}} for course in courses]}
                college_names_from_courses = await department_collection.distinct("College_Name", course_query)
                if college_names_from_courses:
                    query_conditions.append({"College_Name": {"$in": college_names_from_courses}})
                else:
                    logging.warning(f"No colleges found offering courses: {courses}")
                    error_message = f"No colleges found offering the courses: {courses}"
                    if college_names:
                        error_message = f"No colleges named '{college_names}' found offering the courses: {courses}"
                    return {
                        "colleges": [],
                        "cities": await institute_collection.distinct("City"),
                        "total_records": 0,
                        "error_message": error_message,
                        "error_type": "course_not_found"
                    }
            
            query = {"$and": query_conditions} if query_conditions else {}
            all_cities = await institute_collection.distinct("Region")
            total_records = await institute_collection.count_documents(query)
            
            if total_records == 0:
                logging.warning("No college data found for the given search criteria")
                error_message = "No colleges found for the specified search criteria"
                if college_names and courses:
                    error_message = f"No colleges named '{college_names}' found offering the courses: {courses}"
                elif college_names and cities:
                    error_message = f"No colleges named '{college_names}' found in {cities}"
                elif college_names:
                    error_message = f"No colleges found with names: {college_names}"
                elif courses:
                    error_message = f"No colleges found offering the courses: {courses}"
                elif cities:
                    error_message = f"No colleges found in: {cities}"
                return {
                    "colleges": [],
                    "cities": all_cities,
                    "total_records": 0,
                    "error_message": error_message,
                    "error_type": "no_results"
                }
            
            # Build sort criteria for database-level sorting
            sort_criteria = None
            if sort_by:
                sort_direction = 1 if order and order.lower() == "asc" else -1
                sort_mapping = {
                    "placement_percentage": "Overall_College_Placement_Percentage",
                    "fees": "Annual_Fees_(INR)",
                    "rating": "College_Reviews_out_of_5",
                    "name": "College_Name"
                }
                
                db_field = sort_mapping.get(sort_by.lower())
                if db_field:
                    sort_criteria = [(db_field, sort_direction)]
            
            # Execute query with database-level sorting
            if sort_criteria:
                colleges_cursor = institute_collection.find(query).sort(sort_criteria)
            else:
                colleges_cursor = institute_collection.find(query)
            
            colleges_list = await colleges_cursor.to_list(length=None)
            result_colleges = []
            
            for college in colleges_list:
                college_dict = dict(college)
                department_query = {"SJ_Institute_Code":  college.get("SJ_Institute_Code")}
                all_departments = await department_collection.find(department_query).to_list(length=None)
                
                if courses:
                    course_departments = []
                    for dept in all_departments:
                        if "Courses_Offered" in dept and dept["Courses_Offered"] and any(course.lower() in dept["Courses_Offered"].lower() for course in courses):
                            course_departments.append(dept)
                    if not course_departments:
                        if college_names and college.get("College_Name", "") in college_names:
                            college_dict["course_not_found"] = True
                            college_dict["course_not_found_message"] = f"This college does not offer the courses: {courses}"
                        if not college_names and not cities and not filters:
                            continue
                    departments = course_departments
                else:
                    departments = all_departments
                
                college_dict["departments"] = departments
                college_dict["Region"] = college.get('Region',None)


                # Fetch all cutoff docs for this college, get latest year, then max GOPENS for that year
                cutoff_query = {"SJ_Institute_Code": college.get("SJ_Institute_Code")}
                if courses:
                    cutoff_query["$or"] = [{"Course_Name": {"$regex": course, "$options": "i"}} for course in courses]

                # Find all cutoffs for this college
                cutoff_docs = await cutoff_collection.find(cutoff_query).to_list(length=None)
                latest_year = None
                max_score = None
                min_score = None

                # Score fields to evaluate
                score_fields = [
                    "GOPENS", "GSCS", "GSTS", "GVJS",
                    "GNT1S", "GNT2S", "GNT3S", "GOBCS",
                    "LOPENS", "LSCS", "LNT2S", "LOBCS",
                    "DEFOPENS", "TFWS", "DEFROBCS", "EWS"
                ]

                if cutoff_docs:
                    # Find the latest year
                    years = [doc.get("Year") for doc in cutoff_docs if doc.get("Year") is not None]
                    if years:
                        latest_year = max(years)
                        # Get all docs for latest year
                        latest_year_docs = [doc for doc in cutoff_docs if doc.get("Year") == latest_year]
                        all_scores = []
                        for doc in latest_year_docs:
                            for field in score_fields:
                                val = doc.get(field)
                                try:
                                    score = float(val)
                                    all_scores.append(score)
                                except (ValueError, TypeError):
                                    continue
                        if all_scores:
                            max_score = max(all_scores)
                            min_score = min(all_scores)

                college_dict["latest_cet_cutoff_max"] = max_score
                college_dict["latest_cet_cutoff_min"] = min_score
                college_dict["latest_cet_cutoff_year"] = latest_year
                result_colleges.append(college_dict)
            
            return {
                "colleges": result_colleges,
                "cities": sorted(set(all_cities)),
                "total_records": total_records
            }
        except LookupError as e:
            logging.error(f"Lookup error: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error occurred while searching colleges: {e}", exc_info=True)
            return {
                "error": "An unexpected error occurred while searching colleges.",
                "status_code": 500,
                "colleges": [],
                "cities": [],
                "total_records": 0
            }

    async def get_institute_meta_by_sj_code(self, sj_code: int, locations: Optional[list[str]] = None) -> dict:
        """
        Fetch all data for institute_meta using SJ_Institute_Code and optionally filter by City if locations is provided and non-empty.
        Returns the full document with {'_id': 0}.
        """
        try:
            db = await get_db()
            institute_collection = db[settings.INSTIUTE_META_COLLECTION]
            if locations is not None and len(locations) > 0 and not "ALL" in locations:
                # Combine SJ_Institute_Code and $or for City regexes using $and
                query = {
                    "$and": [
                        {"SJ_Institute_Code": sj_code},
                        {"$or": [{"Region": {"$regex": loc, "$options": "i"}} for loc in locations]}
                    ]
                }
            else:
                query = {"SJ_Institute_Code": sj_code}
            result = await institute_collection.find_one(query, {"_id": 0})
            if not result:
                raise LookupError(f"No institute found with SJ_Institute_Code: {sj_code}" + (f" and City in {locations}" if locations else ""))
            return result
        except LookupError:
            # Re-raise LookupError as it is already properly formatted
            raise
        except Exception as e:
            logging.error(f"Error fetching institute_meta by SJ_Institute_Code: {e}")
            raise Exception(f"Database error while fetching institute data: {str(e)}")

    async def get_departments_by_college_name(self, sj_code: int) -> list:
        """
        Fetch all department_meta documents for a given college name.
        Returns the documents with {'_id': 0}.
        """
        try:
            db = await get_db()
            department_collection = db[settings.DEPARTMENT_META_COLLECTION]
            cursor = department_collection.find({"SJ_Institute_Code": sj_code}, {"_id": 0})
            departments = await cursor.to_list(length=None)
            return departments
        except Exception as e:
            logging.error(f"Error fetching department_meta by SJ_Institute_Code: {e}")
            raise Exception(f"Database error while fetching department data: {str(e)}")

    async def get_cutoff_data_for_admission_chances(self, sj_institute_id: int, course_name: str, category: str = "GOPENS") -> dict:
        """
        Fetch cutoff data for a specific college, course, and category, returning the latest year's data.
        """
        try:
            db = await get_db()
            cutoff_collection = db[settings.COLLEGE_CUTOFF_COLLECTION]
            
            # Find cutoff data for the specific college and course
            query = {
                "SJ_Institute_Code": sj_institute_id,
                "Course_Name": {"$regex": course_name, "$options": "i"}
            }
            
            # Get all cutoff data for this college and course, sorted by year descending
            cursor = cutoff_collection.find(query).sort("Year", -1)
            cutoff_data = await cursor.to_list(length=None)
            
            if not cutoff_data:
                raise LookupError(f"No cutoff data found for college '{sj_institute_id}' and course '{course_name}'")
            
            # Return the latest year's data (first in the sorted list)
            latest_cutoff = cutoff_data[0]
            
            # Check if the specified category exists in the cutoff data
            if category not in latest_cutoff or latest_cutoff[category] is None:
                raise ValueError(f"Category '{category}' not found or has no data for college '{sj_institute_id}' and course '{course_name}'")
            
            # Get the cutoff value for the specified category
            cutoff_value = latest_cutoff[category]
            
            # Validate that the cutoff value is numeric
            try:
                float_cutoff = float(cutoff_value)
                if math.isnan(float_cutoff) or math.isinf(float_cutoff):
                    raise ValueError(f"Invalid cutoff value for category '{category}'")
            except (ValueError, TypeError):
                raise ValueError(f"Invalid cutoff value for category '{category}': {cutoff_value}")
            
            return {
                "college_name": latest_cutoff.get("College_Name"),
                "cutoff_value": float_cutoff,
                "year": latest_cutoff.get("Year"),
                "category": category
            }
            
        except (LookupError, ValueError):
            # Re-raise these exceptions as they are already properly formatted
            raise
        except Exception as e:
            logging.error(f"Error fetching cutoff data for admission chances: {e}")
            raise Exception(f"Database error while fetching cutoff data: {str(e)}")

    async def get_institute_meta_by_college_name(self, college_name: str) -> dict:
        """
        Fetch all data for institute_meta using College_Name.
        Returns the full document with {'_id': 0}.
        """
        try:
            db = await get_db()
            institute_collection = db[settings.INSTIUTE_META_COLLECTION]
            result = await institute_collection.find_one({"College_Name": college_name}, {"_id": 0})
            if not result:
                raise LookupError(f"No institute found with College_Name: {college_name}")
            return result
        except LookupError:
            raise
        except Exception as e:
            logging.error(f"Error fetching institute_meta by College_Name: {e}")
            raise Exception(f"Database error while fetching institute data: {str(e)}")

    async def get_cutoff_by_college_name_and_course(self, sj_code: int, course_name: str) -> Optional[dict]:
        """
        Fetch the latest cutoff document for a given college and course (CET by default).
        Returns the full document (all categories) for the latest year.
        """
        try:
            db = await get_db()

            # Escape course_name to make it regex-safe
            safe_course_name = re.escape(course_name)

            query = {
                "SJ_Institute_Code": sj_code,
                "Course_Name": {"$regex": safe_course_name, "$options": "i"}
            }

            cursor = db[settings.COLLEGE_CUTOFF_COLLECTION].find(query, {"_id": 0}).sort("Year", -1).limit(1)
            result = await cursor.to_list(length=1)

            if not result:
                return None
            return result[0]
        except Exception as e:
            logging.error(f"Error fetching cutoff by college and course: {e}")
            raise Exception(f"Database error while fetching cutoff: {str(e)}")

    async def get_all_cutoff_data(self) -> List[dict]:
        """
        For each college and each department (course), return only the cutoff data for the latest year for that department, excluding College_Name.
        """
        try:
            db = await get_db()
            cutoff_collection = db[settings.COLLEGE_CUTOFF_COLLECTION]
            # Fetch all cutoff data
            cursor = cutoff_collection.find({}, {"_id": 0})
            all_cutoff_data = await cursor.to_list(length=None)
            # Group by (SJ_Institute_Code, Course_Name) and keep only the latest year
            latest_cutoff_by_college_course = {}
            for doc in all_cutoff_data:
                key = (doc.get("SJ_Institute_Code"), doc.get("Course_Name"))
                year = doc.get("Year")
                if key not in latest_cutoff_by_college_course or (year is not None and year > latest_cutoff_by_college_course[key].get("Year", -1)):
                    latest_cutoff_by_college_course[key] = doc
            # Remove College_Name from each record
            result = []
            for doc in latest_cutoff_by_college_course.values():
                doc = dict(doc)
                doc.pop("College_Name", None)
                result.append(doc)
            return result
        except Exception as e:
            logging.error(f"Error fetching all cutoff data: {e}")
            raise Exception(f"Database error while fetching all cutoff data: {str(e)}")

    async def get_cutoff_by_category_course_location(self, category: str, courses: list[str],locations:list[str],diploma:bool=False,round_no:int=1) -> list[dict]:
        """
        Fetch all cutoff data from the cutoff collection filtered by category, course, and location, but only the latest year for each (SJ_Institute_Code, Course_Name), sorted by the category value in descending order.
        """
        try:
            db = await get_db()
            if diploma:
                cutoff_collection = db[settings.DIPLOMA_COLLEGE_CUTOFF_COLLECTION]
            else:
                cutoff_collection = db[settings.COLLEGE_CUTOFF_COLLECTION]
            # For partial (substring) matches for each course, use $or with regex
            if courses and locations and not "ALL" in courses and not "ALL" in locations:
                course_regex_or = [{"Course_Name": {"$regex": course, "$options": "i"}} for course in courses]
                location_regex_or = [{"Region": {"$regex": loc, "$options": "i"}} for loc in locations]
                query = {
                    "$and": [
                        {"$or": course_regex_or},
                        {"$or": location_regex_or},
                        {"Year":2024},
                        {"Round":round_no},
                        {category: {"$ne": None}}
                    ]
                }
            elif courses and not "ALL" in courses:
                course_regex_or = [{"Course_Name": {"$regex": course, "$options": "i"}} for course in courses]
                query = {
                    "$and": [
                        {"$or": course_regex_or},
                        {"Year":2024},
                        {"Round":round_no},
                        {category: {"$ne": None}}
                    ]
                }
            elif locations and not "ALL" in locations:
                location_regex_or = [{"Region": {"$regex": loc, "$options": "i"}} for loc in locations]
                query = {
                    "$and": [
                        {"$or": location_regex_or},
                        {"Year":2024},
                        {"Round":round_no},
                        {category: {"$ne": None}}
                    ]
                }
            else:
                query = {
                    category: {"$ne": None},
                    "Year": 2024,
                    "Round":1,
                }
            projection = {"_id": 0}
            cursor = cutoff_collection.find(query, projection)
            all_cutoff_data = await cursor.to_list(length=None)
            # Group by (SJ_Institute_Code, Course_Name) and keep only the latest year
            # latest_cutoff_by_college_course = {}
            # for doc in all_cutoff_data:
            #     key = (doc.get("SJ_Institute_Code"), doc.get("Course_Name"))
            #     year = doc.get("Year")
            #     if key not in latest_cutoff_by_college_course or (year is not None and year > latest_cutoff_by_college_course[key].get("Year", -1)):
            #         latest_cutoff_by_college_course[key] = doc
            # # Sort by category value in descending order
            # filtered = [d for d in latest_cutoff_by_college_course.values() if d.get(category) is not None]
            # filtered.sort(key=lambda x: float(x.get(category, 0)), reverse=True)
            return all_cutoff_data
        except Exception as e:
            logging.error(f"Error fetching cutoff data by category, course, and location: {e}")
            raise Exception(f"Database error while fetching cutoff data: {str(e)}")

    async def get_previous_year_round_cutoff(self, round_one_college_choice_code: int,category:str,round: int,diploma:bool=False) -> Optional[dict]:


        """
        Fetch the cutoff data for the previous year's round 2 recommendations.
        """
        try:
            db = await get_db()
            department_meta = db[settings.DEPARTMENT_META_COLLECTION]
            if diploma:
                cutoff_collection = db[settings.DIPLOMA_COLLEGE_CUTOFF_COLLECTION]
            else:
                cutoff_collection = db[settings.COLLEGE_CUTOFF_COLLECTION]
            query = {
                "Choice_Code": round_one_college_choice_code
            }
            department_details = await department_meta.find_one(query)
            if not department_details:
                return None
            
            course_name = department_details.get("Courses_Offered")
            sj_code = department_details.get("SJ_Institute_Code")

            cutoff_query = {
                "SJ_Institute_Code": sj_code,
                "Course_Name":  {"$in":[course_name,course_name.upper(),course_name.lower(),course_name.title()]},
                "Year": 2024,
                "Round": round
            }
            cutoff_data = await cutoff_collection.find_one(cutoff_query)
            if not cutoff_data:
                return None
            last_year_cutoff= cutoff_data.get(category)
            return {
                "last_year_cutoff":last_year_cutoff,
                "course_name":course_name,
                "sj_code":sj_code,
                "category":category,
                "round":round
            }
        except Exception as e:
            logging.error(f"Error fetching cutoff data by category, course, and location: {e}")
            raise Exception(f"Database error while fetching cutoff data: {str(e)}")

    async def get_courses_cutoff(self, courses: list[str],round_no: int,last_year_cutoff:float,category:str,locations:list[str],diploma:bool=False) -> list[dict]:
        """
        Fetch all cutoff data from the cutoff collection filtered by course name, sorted by the category value in descending order.
        """
        try:
            db = await get_db()
            vacant_codes=[]
            if diploma:
                cutoff_collection = db[settings.DIPLOMA_COLLEGE_CUTOFF_COLLECTION]
            else:
                cutoff_collection = db[settings.COLLEGE_CUTOFF_COLLECTION]
            # For partial (substring) matches for each course, use $or with regex         
            if round_no==2 and not diploma:
                provisional_vacant_seat= db[settings.PROVISIONAL_VACANT_SEAT_COLLECTION]
                vacant_codes=await provisional_vacant_seat.distinct('choice_code', {'round': 2})
            if courses and locations and not "ALL" in courses and not "ALL" in locations:
                course_regex_or = [{"Course_Name": {"$regex": course, "$options": "i"}} for course in courses]
                location_regex_or = [{"Region": {"$regex": loc, "$options": "i"}} for loc in locations]
                query = {
                    "$and": [
                        {"$or": course_regex_or},
                        {"$or": location_regex_or},
                        {"Year":2024},
                        {"Round":round_no},
                        {category: {"$gte": last_year_cutoff}}
                    ]
                }
                if vacant_codes:
                    query["$and"].append({"Choice_Code": {"$in": vacant_codes}})
            elif courses and not "ALL" in courses:
                course_regex_or = [{"Course_Name": {"$regex": course, "$options": "i"}} for course in courses]
                query = {
                    "$and": [
                        {"$or": course_regex_or},
                        {"Year":2024},
                        {"Round":round_no},
                        {category: {"$gte": last_year_cutoff}}
                    ]
                }
                if vacant_codes:
                    query["$and"].append({"Choice_Code": {"$in": vacant_codes}})
            elif locations and not "ALL" in locations:
                location_regex_or = [{"Region": {"$regex": loc, "$options": "i"}} for loc in locations]
                query = {
                    "$and": [
                        {"$or": location_regex_or},
                        {"Year":2024},
                        {"Round":round_no},
                        {category: {"$gte": last_year_cutoff}}
                    ]
                }
                if vacant_codes:
                    query["$and"].append({"Choice_Code": {"$in": vacant_codes}})
            else:
                if vacant_codes:
                    query = {
                        category: {"$gte": last_year_cutoff},
                        "Year": 2024,
                        "Round":round_no,
                        "Choice_Code": {"$in": vacant_codes}
                    }
                else:
                    query = {
                        category: {"$gte": last_year_cutoff},
                        "Year": 2024,
                        "Round":round_no,
                    }
            
            cursor = cutoff_collection.find(query)
            all_cutoff_data = await cursor.to_list(length=None)
            return all_cutoff_data
        except Exception as e: 
            logging.error(f"Error fetching cutoff data by category, course, and location: {e}")
            raise Exception(f"Database error while fetching cutoff data: {str(e)}")
           
    async def search_college_by_college_code(self, college_code: int) -> List[dict]:
        """
        Search for colleges by college code.
        """
        try:
            db = await get_db()
            institute_collection = db[settings.INSTIUTE_META_COLLECTION]
            department_meta = db[settings.DEPARTMENT_META_COLLECTION]
            response={}
            query = {"College_Code": college_code}
            institute_result = await institute_collection.find_one(query)
            if not institute_result:
                return None
            response['College_Name'] = institute_result.get('College_Name')
            response['sj_code']=institute_result.get('SJ_Institute_Code')
            response['College_Website'] = institute_result.get('College_Website')
            response['City'] = institute_result.get('City')
            response["College_code"] = institute_result.get('SJ_Institute_Code')
            department_query = {"SJ_Institute_Code": institute_result.get("SJ_Institute_Code")}
            depart_cursor = department_meta.find(department_query)
            department_result = await depart_cursor.to_list(length=None)
            depart_meta=[]
            for dept in department_result:
                depart_meta.append({
                    "course_name": dept.get('Courses_Offered'),
                    "choice_code": dept.get('Choice_Code'),
                    "course_code": dept.get('Course_Code')
                })
            response['department'] = depart_meta
            return response
        except Exception as e:
            logging.error(f"Error in repository while searching college by code: {e}")
            raise Exception(f"Database error while searching college by code: {str(e)}")
    
    async def search_college_by_college_name(self, college_name: str) -> List[dict]:
        """
        Search for colleges by college name.
        """
        try:
            db = await get_db()
            final_response:list[dict]=[]
            institute_collection = db[settings.INSTIUTE_META_COLLECTION]
            department_meta = db[settings.DEPARTMENT_META_COLLECTION]
            query = {"College_Name": {"$regex": college_name, "$options": "i"}}
            cursor = institute_collection.find(query)
            institute_result = await cursor.to_list(length=None)
            for institute in institute_result:
                response={}
                response['College_Name'] = institute.get('College_Name')
                response['College_Website'] = institute.get('College_Website')
                response['sj_code']=institute.get('SJ_Institute_Code')
                response['City'] = institute.get('City')
                response["College_code"] = institute.get('SJ_Institute_Code')
                department_query = {"SJ_Institute_Code": institute.get("SJ_Institute_Code")}
                depart_cursor = department_meta.find(department_query)
                department_result = await depart_cursor.to_list(length=None)
                depart_meta=[]
                for dept in department_result:
                    depart_meta.append({
                        "course_name": dept.get('Courses_Offered'),
                        "choice_code": dept.get('Choice_Code'),
                        "course_code": dept.get('Course_Code')
                    })
                response['department'] = depart_meta
                final_response.append(response)
            return final_response
        except Exception as e:
            logging.error(f"Error in repository while searching college by name: {e}")
            raise Exception(f"Database error while searching college by name: {str(e)}")
        
    async def search_college_by_choice_code(self, choice_code: int,email: str) -> List[dict]:
        """
        Search for colleges by choice code.
        """
        try:
            db = await get_db()
            department_meta = db[settings.DEPARTMENT_META_COLLECTION]
            institute_collection = db[settings.INSTIUTE_META_COLLECTION]
            query = {"Choice_Code": choice_code}
            department_result = await department_meta.find_one({"Choice_Code": choice_code}, {"_id": 0})
            response ={}
            if not department_result:
                return None
            sj_code = department_result.get("SJ_Institute_Code")
            institute_result = await institute_collection.find_one({"SJ_Institute_Code": sj_code}, {"_id": 0})
            if not institute_result:
                return None
            response['College_Name'] = institute_result.get('College_Name')
            response['sj_code']=sj_code
            response['College_Website'] = institute_result.get('College_Website')
            response['City'] = institute_result.get('City')
            response["College_code"] = institute_result.get('College_Code')
            response['department'] = {
                "course_name": department_result.get('Courses_Offered'),
                "choice_code": department_result.get('Choice_Code'),
                "course_code": department_result.get('Course_Code')
            }

            return response
        except Exception as e:
            logging.error(f"Error in repository while searching college by choice code: {e}")
            raise Exception(f"Database error while searching college by choice code: {str(e)}")

    async def store_diploma_user_config(self, payload: DiplomaUserConfig,email: str):
        """
        Store user config for diploma.
        """
        try:
            db = await get_db()
            user_collection = db[settings.DIPLOMA_USER_CONFIG_COLLECTION]
            query = {"email": email,"Round":payload.round}
            update = {"$set": {"diploma_user_config": payload.dict()}}
            await user_collection.update_one(query, update, upsert=True)
        except Exception as e:
            logging.error(f"Error in repository while storing diploma user config: {e}")
    async def get_diploma_user_config(self,email: str,round:int):
        """
        Get user config for diploma.
        """
        try:
            db = await get_db()
            user_collection = db[settings.DIPLOMA_USER_CONFIG_COLLECTION]
            query = {"email": email,"Round":round}

            user_config = await user_collection.find_one(query, {"_id": 0})
            return user_config.get("diploma_user_config")
        except Exception as e:
            logging.error(f"Error in repository while getting diploma user config: {e}")
    
