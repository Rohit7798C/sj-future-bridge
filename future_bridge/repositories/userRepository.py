from future_bridge.utils.db import get_cj_db,get_db
from future_bridge.config.config import settings
from future_bridge.schema.userSchema import UserRequest
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
import logging
from future_bridge.models.userModel import User,Feedback,RoundPreferences
from future_bridge.schema.recommendationSchema import CollegeDetails

class UserRepository:

    async def read_user(self, user: User) -> User | None:
        """
        Reads user details from the DB
        Args:
            user: User Model with username to search for
        Returns:
            User: User Model updated with details (username and questionnaire)
        """
        logging.info(f"Reading User - {user.username}")
        db = await get_cj_db()
        reply = await db[settings.USER_COLLECTION].find_one({'username': user.username}, {'_id': 0})

        if reply is None:
            return None

        # Remove MongoDB _id field before creating User model
        return User(**reply)

    async def store_user(self, user: User) -> Dict[str, Any]:
        """
        Store user data in the CJ_DATABASE user collection
        """
        try:
            # Convert model to dict and add timestamps in ISO format IST
            user_data = user.model_dump()

            # Get database connection to CJ_DATABASE
            db = await get_cj_db()
            collection = db[settings.USER_COLLECTION]
            
            # Insert the document
            result = await collection.insert_one(user_data)
            
            if not result.inserted_id:
                raise Exception("Failed to store user data")
            
            return {
                "user_id": str(result.inserted_id) }
            
        except ValueError as e:
            raise
        except Exception as e:
            raise Exception(f"Failed to store user: {str(e)}")

    async def store_feedback(self, feedback_data: Feedback) -> Dict[str, Any]:
        """
        Store feedback data in the CJ_DATABASE feedback collection
        """
        try:
            # Convert model to dict and add timestamps in ISO format IST
            feedback_data = feedback_data.model_dump()

            # Get database connection to CJ_DATABASE
            db = await get_db()
            collection = db[settings.FEEDBACK_COLLECTION]
            filter_query = {"username": feedback_data.get("username")} 
            # Insert the document
            result = await collection.update_one(filter_query, {"$set": feedback_data}, upsert=True)
            
            if not result.acknowledged:
                raise Exception("Failed to store feedback data")
            
            return {
                "feedback_status": str(result.acknowledged)
            }
        except ValueError as e:
            raise
        except Exception as e:
            raise Exception(f"Failed to store feedback: {str(e)}")

    async def store_college_details(self, college_data: CollegeDetails,email:str) -> Dict[str, Any]:

        """
        Store college details data in the CJ_DATABASE college collection
        """
        try:
            # Convert model to dict and add timestamps in ISO format IST
            college_data = college_data.model_dump()

            # Get database connection to CJ_DATABASE
            db = await get_db()
            collection = db[settings.USER_ROUND_COLLECTION]
            
            # Insert the document
            result = await collection.update_one(
                {"email": email,"round":college_data.get("round")},
                {"$set": college_data},
                upsert=True
            )
            
            if not result.acknowledged:
                raise Exception("Failed to store college details data")
            
            return {
                "college_status": str(result.acknowledged),
            }
        except ValueError as e:
            raise
        except Exception as e:
            raise Exception(f"Failed to store college details: {str(e)}")
    
    async def get_user_round_details(self,email:str,round:int) -> Dict[str, Any]:

        """
        Get user round details data from the database
        
        Args:
            email: str
        Returns:
            Dict[str, Any]: A dictionary containing the user_id and a message
        """
        db = await get_db()
        collection = db[settings.USER_ROUND_COLLECTION]
        result = await collection.find_one({"email": email,"round":round})
        if result:
            return  {  
            "username":result["email"],
            "College_Name":result["college_name"],
            "College_code":result["college_code"],
            "City":result["location"],
            "Course_Name":result["course_name"],
            "Course_Code":result["course_code"],
            "Choice_Code":result["choice_code"],
            "round":result["round"],
        }
        else:
            return {}

    async def store_user_round_preferences(self, payload: RoundPreferences,email:str) -> Dict[str, Any]:
        """
        Store user round preferences in the database
        Args:
            payload: RoundPreferences
        Returns:
            Dict[str, Any]: A dictionary containing the user_id and a message
        """
        db = await get_db()
        collection = db[settings.USER_ROUND_PREFERENCES]
        result = await collection.update_one(
            {"email": email,"round":payload.round},
            {"$set": payload.model_dump()},
            upsert=True
        )
        if result.acknowledged:
            return {
                "round_status": str(result.acknowledged),
            }
        else:
            raise Exception("Failed to store user round preferences")
    
    async def get_user_round_preferences(self,email:str,round:int) -> Dict[str, Any]:
        """
        Get user round preferences from the database
        Args:
            email: str
        Returns:
            Dict[str, Any]: A dictionary containing the user_id and a message
        """
        db = await get_db()
        collection = db[settings.USER_ROUND_PREFERENCES]
        result = await collection.find_one({"email": email,"round":round})
        if result:
            return {
                "round":result["round"],
                "branches":result["branches"],
                "cities":result["cities"],
            }
        else:
            return {}

def get_user_repository() -> UserRepository:
    return UserRepository() 