from calendar import c
import logging
from this import d

from fastapi import Query
from future_bridge.utils.db import get_db,get_cj_db
from future_bridge.config.config import settings
from future_bridge.models.commonModel import OTPValidator,CollegeConfigurationRequest,RoundPreferencesRequest,CollegeRoundPrefrence
from future_bridge.schema.recommendationSchema import CollegeRecommendationGroupResponse
from collections import defaultdict



class OTPValidatorRepo:
    """
    Used for performing operations on test_questionSet collection in the database.
    """
    async def store_otp(self,data:OTPValidator)-> bool:
        """
        Inserts a new OTP Data into the collection.

        Args:
            job (HRJob): HRJob object containing job details.

        Returns:
            bool: True if the job was created successfully, False otherwise.
        """
        logging.info('Creating a new OTP Validation Row...')
        db = await get_cj_db()
        otp_data=await db[settings.OTP_VALIDATOR].find_one({"useremail": data.__dict__.get('useremail')})
        if otp_data:
            await db[settings.OTP_VALIDATOR].delete_many({"useremail": data.__dict__.get('useremail')})

        result = await db[settings.OTP_VALIDATOR].insert_one(data.__dict__)
        if not result.inserted_id:
            raise Exception("Failed to store OTP.")
        return True
    
    async def validate_otp(self, email:str, otp:str, user_type: str) -> dict:
        db = await get_cj_db()
        try:
            otp = int(otp)
        except ValueError:
            logging.warning(f"Invalid OTP format provided: {otp}")
            return {"isValidOtp": False,"message": "Invalid OTP format"}

        otp_data= await db[settings.OTP_VALIDATOR].find_one({"useremail": email, "otp": otp})
        if otp_data is None:
            return {"isValidOtp":False}

        # Collection and field mapping
        type_config = {
            'user': (settings.USERS_COLLECTION, 'profileIcon', 'name', 'username'),
            'counsellor': (settings.CONUSELOR_INFO, 'ProfileURL', 'Name', 'counsellorEmail'),
            'hr': (settings.HR_INFO, 'photo_url', 'name', 'email'),
            'college_admin': (settings.COLLEGE_ADMIN_COLLECTION, 'photo_url', 'name', 'email')
        }
        collection_name, profile_field, name_field, email_field = type_config.get(user_type, (settings.USERS_COLLECTION, 'profileIcon', 'name', 'username'))
        
        user_data = await db[collection_name].find_one({email_field: email}, {"_id": 0, name_field : 1, profile_field: 1})
        return {
            "isValidOtp": True,
            "name": user_data.get(name_field) if user_data else None,
            "profileIcon": user_data.get(profile_field) if user_data else None
        }


class CommonRepo:
    async def store_college_config(self, college_config: CollegeConfigurationRequest,email:str):
        db = await get_db()
        result = await db[settings.COLLEGE_CONFIG].update_one({"useremail": email,"exam_type":college_config.exam_type}, {"$set": college_config.__dict__}, upsert=True)

        if not result.acknowledged:
            raise Exception("Failed to store college configuration.")
        return result.modified_count or result.upserted_id
    
    async def get_college_config(self, email: str):
        db = await get_db()
        query={"useremail": email}
        result = await db[settings.COLLEGE_CONFIG].find(query,{"_id":0}).to_list(length=100)

        if not result:
            return None
        return result

    
    async def store_round_preferences(self, round_preferences: RoundPreferencesRequest,email:str):
        db = await get_db()
        query={
            "useremail": email,
            "round_no":round_preferences.round_no,
            "exam_type":round_preferences.exam_type
        }
        result = await db[settings.COMMON_ROUND_PREFERENCES].update_one(query, {"$set": round_preferences.__dict__}, upsert=True)

        if not result.acknowledged:
            raise Exception("Failed to store round preferences.")
        return result.modified_count or result.upserted_id

    async def get_round_preferences(self, round_no: int,email:str,exam_type:str):
        db = await get_db()
        query={"useremail": email,"round_no":round_no,"exam_type":exam_type}
        result = await db[settings.COMMON_ROUND_PREFERENCES].find_one(query,{"_id":0})
        if not result:
            return None
        return result
    
    async def generate_recommendations(self, round_preferences: RoundPreferencesRequest,email:str):
        db = await get_db()
        query={"useremail": email,"round_no":round_preferences.round_no,"exam_type":round_preferences.exam_type}
        result = await db[settings.USER_ROUND_PREFERENCES].find(query,{"_id":0}).to_list(length=100)
        if not result:
            return None
        return result

    async def get_recommendations(self,round_no: int,email:str,exam_type:str):

        db = await get_db()
        query={"useremail": email,"round_no":round_no,"exam_type":exam_type}
        result = await db[settings.COMMON_RECOMMENDATIONS].find(query,{"_id":0}).to_list(length=100)

        if not result:
            return None
        return result

    async def store_college_recommendations(self, college_recommendation: CollegeRecommendationGroupResponse,round_no: int,exam_type:str):

        db = await get_db()
        query={
            "useremail": college_recommendation.username,
            "round_no":round_no,
            "exam_type":exam_type
        }

        data ={
            "useremail": college_recommendation.username,
            "round_no":round_no,
            "exam_type":exam_type,
            "Dream": college_recommendation.Dream,
            "Reach": college_recommendation.Reach,
            "Match": college_recommendation.Match,
            "Safety": college_recommendation.Safety,
            "Round": college_recommendation.Round,
            "is_payment": college_recommendation.is_payment,
            "accept_payment": college_recommendation.accept_payment,
        }
        result = await db[settings.COMMON_RECOMMENDATIONS].update_one(query, {"$set": data}, upsert=True)

        if not result.acknowledged:
            raise Exception("Failed to store college recommendations.")
        return result.modified_count or result.upserted_id

    async def get_cutoff_data(self, exam_type: str, category: str, round_no: int=1,previous_year_cutoff_dict: dict={},branchs: list=None,locations: list=None,gender: str=None,district: str=None):
        previous_year_cutoff=0
        db = await get_db()
        home_university_district = []
        other_universities_district=[]
        consider_l=True if gender=="female" else False
        collection=db[settings.UNIVERSITY_MAPPING]
        projection = {"_id": 0}
        home_university_cutoff_data=[]
        other_university_cutoff_data=[]
        state_university_cutoff_data=[]

        doc = await collection.find_one({"District": district}, {"University": 1, "_id": 0})
        if doc and "University" in doc:
            home_university_district_to_consider = sorted(
                await collection.distinct("District", {"University": doc["University"]})
            )
            distinct_district=await collection.distinct("District")
            other_universities_to_consider = list(set(distinct_district) - set(home_university_district_to_consider))


        if exam_type=="BCA_MCA_Int":
            collection=db[settings.BCA_COLLEGE_CUTOFF_COLLECTION]
        elif exam_type=="BBA_BMS_BBM_MBA_Int":  
            collection=db[settings.BBA_COLLEGE_CUTOFF_COLLECTION]
        elif exam_type=="B_and_D_Pharmacy":
            collection=db[settings.PHARMACY_COLLEGE_CUTOFF_COLLECTION]

        if home_university_district_to_consider and category[-1]=="H":
            categories_list=[]
            if consider_l:
                categories_list=[category,"L"+category[1:]]
                previous_year_cutoff= previous_year_cutoff_dict.get(categories_list[0],previous_year_cutoff) 
                previous_year_cutoff_l= previous_year_cutoff_dict.get(categories_list[1],previous_year_cutoff) 
                if previous_year_cutoff_l<previous_year_cutoff:
                    previous_year_cutoff=previous_year_cutoff_l
            else:
                categories_list=[category]
                previous_year_cutoff= previous_year_cutoff_dict.get(category,previous_year_cutoff)

            query = {
                "Year": 2024,
                "Round": round_no,
                **({"City": {"$in": locations}} if locations and not "ALL" in locations else {}),
                "District": {"$in": home_university_district_to_consider}
            }
    
            # Condition for categories
            category_condition = {
                "$or": [
                    {cat: {"$ne": None, **({"$gt": float(previous_year_cutoff)} if previous_year_cutoff else {})}}
                    for cat in categories_list
                ]
            }

            # Condition for branches
            branch_condition = {
                "$or": [
                    {"Course Name": branch}
                    for branch in branchs
                ]
            } if branchs and "ALL" not in branchs else {}

            # Combine
            if branch_condition:
                query["$and"] = [category_condition, branch_condition]
            else:
                query.update(category_condition)

            cursor = collection.find(query, projection)
            home_university_cutoff_data = await cursor.to_list(length=None)

            
        if other_universities_to_consider and category[-1]=="H":
            if consider_l:
                categories_list=[category[:-1]+"O","L"+category[1:-1]+"O"]
                previous_year_cutoff= previous_year_cutoff_dict.get(categories_list[0],previous_year_cutoff) 
                previous_year_cutoff_l= previous_year_cutoff_dict.get(categories_list[1],previous_year_cutoff) 
                if previous_year_cutoff_l<previous_year_cutoff:
                    previous_year_cutoff=previous_year_cutoff_l
            else:
                categories_list=[category[:-1]+"O"]
                previous_year_cutoff= previous_year_cutoff_dict.get(categories_list[0],previous_year_cutoff)
            query = {
                "Year": 2024,
                "Round": round_no,
                **({"City": {"$in": locations}} if locations and not "ALL" in locations else {}),
                "District": {"$in": other_universities_to_consider}
            }

            category_condition = {
                    "$or": [
                        {cat: {"$ne": None, **({"$gt": float(previous_year_cutoff)} if previous_year_cutoff else {})}}
                        for cat in categories_list
                    ]
            }
            
            # Condition for branches
            branch_condition = {
                "$or": [
                    {"Course Name": branch}
                    for branch in branchs
                ]
            } if branchs and "ALL" not in branchs else {}

            # Combine
            if branch_condition:
                query["$and"] = [category_condition, branch_condition]
            else:
                query.update(category_condition)
            cursor = collection.find(query, projection)
            other_university_cutoff_data = await cursor.to_list(length=None)

        query={
            "Year":2024,
            "Round":round_no,
            **({"City": {"$in": locations}} if locations and not "ALL" in locations else {})
        }
        branch_condition = {
            "$or": [
                {"Course Name": branch}
                for branch in branchs
            ]
        } if branchs and "ALL" not in branchs else {}

        # 
        if consider_l:
            categories_list=[category[:-1]+"S","L"+category[1:-1]+"S"]
            previous_year_cutoff= previous_year_cutoff_dict.get(categories_list[0],previous_year_cutoff) 
            previous_year_cutoff_l= previous_year_cutoff_dict.get(categories_list[1],previous_year_cutoff) 
            if previous_year_cutoff_l<previous_year_cutoff:
                previous_year_cutoff=previous_year_cutoff_l
        else:
            categories_list=[category[:-1]+"S"]
            previous_year_cutoff= previous_year_cutoff_dict.get(categories_list[0],previous_year_cutoff)
        if category[-1]!="H":
            categories_list.append(category)
            previous_year_cutoff= previous_year_cutoff_dict.get(category,previous_year_cutoff)
        category_condition = {
                "$or": [
                    {cat: {"$ne": None, **({"$gt": float(previous_year_cutoff)} if previous_year_cutoff else {})}}
                    for cat in categories_list
                ]
        }
        
        # Combine
        if branch_condition:
            query["$and"] = [category_condition, branch_condition]
        else:
            query.update(category_condition)
        cursor = collection.find(query, projection)
        state_university_cutoff_data = await cursor.to_list(length=None)
        if not state_university_cutoff_data and not home_university_cutoff_data and not other_university_cutoff_data:
            return None

        return {"home_university_cutoff_data":home_university_cutoff_data,"other_university_cutoff_data":other_university_cutoff_data,"state_university_cutoff_data":state_university_cutoff_data}

    async def get_previous_year_cutoff(self, exam_type: str, category: str, round_no: int, last_college_round_choice_code: str):
        db = await get_db()
        if exam_type=="BCA_MCA_Int":
            collection=db[settings.BCA_COLLEGE_CUTOFF_COLLECTION]
        elif exam_type=="BBA_BMS_BBM_MBA_Int":  
            collection=db[settings.BBA_COLLEGE_CUTOFF_COLLECTION]
        elif exam_type=="B_and_D_Pharmacy":
            collection=db[settings.PHARMACY_COLLEGE_CUTOFF_COLLECTION]
        query = {
            "Course Code": last_college_round_choice_code
        }
        result = await collection.find_one(query, {"_id": 0})
        return result
    
    async def search_college_by_name(self, college_name: str,exam_type:str):
        db = await get_db()
        if exam_type=="BCA_MCA_Int":
            collection=db[settings.BCA_COLLEGE_CUTOFF_COLLECTION]
        elif exam_type=="BBA_BMS_BBM_MBA_Int":  
            collection=db[settings.BBA_COLLEGE_CUTOFF_COLLECTION]
        elif exam_type=="B_and_D_Pharmacy":
            collection=db[settings.PHARMACY_COLLEGE_CUTOFF_COLLECTION]
        query = {
            "College Name": {"$regex": college_name, "$options": "i"},
            "Round":1
        }
        projection={
            "College Name":1,
            "College Code":1,
            "Course Code":1,
            "Course Name":1,
            "City":1,
            "District":1,
            "_id":0
        }
        result = await collection.find(query,projection).to_list(length=None)
        if not result:
            raise ValueError("College not found")

        grouped = defaultdict(lambda: {"College Name": "", "College Code": "", "Courses": []})

        for doc in result:
            college_code = doc["College Code"]
            grouped[college_code]["College Name"] = doc["College Name"]
            grouped[college_code]["College Code"] = college_code
            
            # Append course info
            grouped[college_code]["Courses"].append({
                "Course Name": doc["Course Name"],
                "Course Code": doc["Course Code"]
            })

        # Convert back to list if needed
        final_result = list(grouped.values())
        return final_result
    
    async def search_college_by_college_code(self, college_code: int,exam_type:str):
        db = await get_db()
        if exam_type=="BCA_MCA_Int":
            collection=db[settings.BCA_COLLEGE_CUTOFF_COLLECTION]
        elif exam_type=="BBA_BMS_BBM_MBA_Int":  
            collection=db[settings.BBA_COLLEGE_CUTOFF_COLLECTION]
        elif exam_type=="B_and_D_Pharmacy":
            collection=db[settings.PHARMACY_COLLEGE_CUTOFF_COLLECTION]
        query = {
            "College Code": college_code,
            "Round":1
        }
        projection={
            "College Name":1,
            "College Code":1,
            "Course Code":1,
            "Course Name":1,
            "City":1,
            "District":1,
            "_id":0
        }
        result = await collection.find(query,projection).to_list(length=None)
        if not result:
            raise ValueError("College not found")
        grouped = defaultdict(lambda: {"College Name": "", "College Code": "", "Courses": []})

        for doc in result:
            college_code = doc["College Code"]
            grouped[college_code]["College Name"] = doc["College Name"]
            grouped[college_code]["College Code"] = college_code
            
            # Append course info
            grouped[college_code]["Courses"].append({
                "Course Name": doc["Course Name"],
                "Course Code": doc["Course Code"]
            })

        # Convert back to list if needed
        final_result = list(grouped.values())
        return final_result

    
    async def search_college_by_choice_code(self, choice_code: str,exam_type:str):
        db = await get_db()
        if exam_type=="BCA_MCA_Int":
            collection=db[settings.BCA_COLLEGE_CUTOFF_COLLECTION]
        elif exam_type=="BBA_BMS_BBM_MBA_Int":  
            collection=db[settings.BBA_COLLEGE_CUTOFF_COLLECTION]
        elif exam_type=="B_and_D_Pharmacy":
            collection=db[settings.PHARMACY_COLLEGE_CUTOFF_COLLECTION]
        query = {
            "Course Code": {"$regex": choice_code, "$options": "i"}
        }
        projection={
            "College Name":1,
            "College Code":1,
            "Course Code":1,
            "Course Name":1,
            "City":1,
            "District":1,
            "_id":0
        }
        result = await collection.find_one(query, projection)
        if not result:
            raise ValueError("College not found")
        return result

    async def store_round_college_preference(self, payload: CollegeRoundPrefrence,email:str):
        db = await get_db()
        collection=db[settings.ROUND_COLLEGE_PREFERENCE_COLLECTION]
        query = {
            "email": email,
            "exam_type": payload.exam_type,
            "round_no": payload.round_no
        }
        projection={
            "email":1,
            "exam_type":1,
            "round_no":1,
            "_id":0
        }
        result = await collection.find_one(query, projection)
        if result:
            data = payload.model_dump()
            data["email"] = email
            await collection.update_one(query, {"$set": data})
        else:
            data = payload.model_dump()
            data["email"] = email
            await collection.insert_one(data)
        
    async def get_round_college_preference(self, email: str, exam_type: str, round_no: int):
        db = await get_db()
        collection=db[settings.ROUND_COLLEGE_PREFERENCE_COLLECTION]
        query = {
            "email": email,
            "exam_type": exam_type,
            "round_no": round_no
        }
        projection={
            "_id":0
        }
        result = await collection.find_one(query, projection)
        if result:
            return result
        else:
            raise ValueError("Preference not found")    
    

    

