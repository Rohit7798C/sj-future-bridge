from fastapi import Query
from future_bridge.utils.db import get_db
from future_bridge.config.config import settings
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from future_bridge.schema.recommendationSchema import RecommendationRequest,CollegeRecommendationGroupResponse
from typing import Optional, List, Dict, Any

class RecommendationRepository:
    
    
    async def store_recommendation(self, request_data: RecommendationRequest) -> Dict[str, Any]:
        """
        Store recommendation data in the database
        
        Args:
            request_data: Pydantic model containing recommendation data
            
        Returns:
            Dict[str, Any]: A dictionary containing the recommendation_id and created_at timestamp
            
        Raises:
            ValueError: If data validation fails
            Exception: If database operation fails
        """
        try:
            # Convert model to dict with aliases preserved and add timestamps in ISO format IST
            recommendation_data = request_data.model_dump(by_alias=True)
            ist_timezone = timezone(timedelta(hours=5, minutes=30))
            current_time = datetime.now(ist_timezone).isoformat()
            recommendation_data["created_at"] = current_time
            recommendation_data["updated_at"] = current_time
            
            # Get database connection
            db = await get_db()
            collection = db[settings.USER_RECOMMENDATIONS_COLLECTION]
            
            # Insert the document
            result = await collection.insert_one(recommendation_data)
            
            if not result.inserted_id:
                raise Exception("Failed to store recommendation data")
            
            return {
                "recommendation_id": str(result.inserted_id),
                "created_at": current_time
            }
            
        except ValueError as e:
            raise
        except Exception as e:
            raise Exception(f"Failed to store recommendation: {str(e)}")

    async def get_latest_recommendation_by_email(self, email: str) -> Optional[dict]:
        """
        Fetch the latest recommendation for a user by email, sorted by _id descending.
        Returns the most recent recommendation document or None if not found.
        """
        db = await get_db()
        collection = db[settings.USER_RECOMMENDATIONS_COLLECTION]
        doc = await collection.find_one({"username": email}, sort=[("_id", -1)])
        return doc

    async def store_college_recommendations(self, college_recommendation:CollegeRecommendationGroupResponse,round:int=1,diploma:bool=False)-> Dict[str, Any]:
        """
        Store college recommendations for a user by email.
        """
        recommendation_data = college_recommendation.model_dump(by_alias=True)
        recommendation_data["Round"] = round
        db = await get_db()
        if diploma:
            collection = db[settings.DIPLOMA_RECOMMENDATIONS_COLLECTION]
        else:
            collection = db[settings.RECOMMENDATIONS_COLLECTION]
        filter_query = {"username": college_recommendation.username,"Round":round} 
        result = await collection.update_one(filter_query, {"$set": recommendation_data}, upsert=True)
        
        if not result.acknowledged:
            raise Exception("Failed to store feedback data")
        
        return {
            "acknowledged": result.acknowledged
        }

    async def get_college_recommendations_by_email(self, email: str,round:int=1,diploma:bool=False) -> Optional[CollegeRecommendationGroupResponse]:
        """
        Fetch college recommendations for a user by email.
        """
        db = await get_db()
        if diploma:
            collection = db[settings.DIPLOMA_RECOMMENDATIONS_COLLECTION]
            query = {"username": email, "Round": round}
        else:
            collection = db[settings.RECOMMENDATIONS_COLLECTION]
            query = {"username": email}
        doc = await collection.find_one(query)
        if doc:
            return CollegeRecommendationGroupResponse(**doc)
        return None