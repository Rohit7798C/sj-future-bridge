from fastapi import Depends
from future_bridge.repositories.userRepository import UserRepository, get_user_repository
from typing import Dict, Any
from future_bridge.services.errorService import UserAlreadyExistsError
from future_bridge.models.userModel import User,Feedback
from future_bridge.schema.userSchema import UserRequest,FeedBack,RoundPreferences
from future_bridge.schema.recommendationSchema import CollegeDetails

class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def store_user(self, request_data: UserRequest) -> Dict[str, Any]:
        """
        Store user data in the database if not already present
        
        Args:
            request_data: Pydantic model containing user data
        Returns:
            Dict[str, Any]: A dictionary containing the user_id and a message
        """
        # Initialize User model
        user = User(**request_data.model_dump())
        
        # Check if user already exists
        existing_user = await self.user_repository.read_user(user)
        if existing_user:
            raise UserAlreadyExistsError(user.username)
        
        # Store new user
        result = await self.user_repository.store_user(user)
        return result

    async def store_feedback(self, feedback_data: FeedBack) -> Dict[str, Any]:
        """
        Store feedback data in the database
        
        Args:
            feedback_data: Pydantic model containing feedback data
        Returns:
            Dict[str, Any]: A dictionary containing the feedback_id and a message
        """
        # Initialize Feedback model
        feedback = Feedback(**feedback_data.model_dump())
        
        # Store new feedback
        result = await self.user_repository.store_feedback(feedback)
        return result

    async def store_college_details(self, college_data: CollegeDetails,email:str) -> Dict[str, Any]:

        """
        Store college details data in the database
        
        Args:
            college_data: Pydantic model containing college details data
        Returns:
            Dict[str, Any]: A dictionary containing the college_id and a message
        """
        # Initialize CollegeDetails model
        college = CollegeDetails(**college_data.model_dump())
        
        result = await self.user_repository.store_college_details(college,email)
        return result
    
    async def get_college_details(self,email:str) -> Dict[str, Any]:
        """
        Get college details data from the database
        
        Args:
            email: str
        Returns:
            Dict[str, Any]: A dictionary containing the college_id and a message
        """
        result = await self.user_repository.get_college_details(email)
        return result
    
    async def get_user_round_details(self,email:str,round:int) -> Dict[str, Any]:
        """
        Get user round details data from the database
        
        Args:
            email: str
        Returns:
            Dict[str, Any]: A dictionary containing the user_id and a message
        """
        result = await self.user_repository.get_user_round_details(email,round)
        return result
    async def store_user_round_preferences(self, payload: RoundPreferences,email:str) -> Dict[str, Any]:
        """
        Store user round preferences in the database
        Args:
            payload: RoundPreferences
        Returns:
            Dict[str, Any]: A dictionary containing the user_id and a message
        """
        result = await self.user_repository.store_user_round_preferences(payload,email)
        return result
    
    async def get_user_round_preferences(self,email:str,round:int) -> Dict[str, Any]:
        """
        Get user round preferences from the database
        Args:
            email: str
        Returns:
            Dict[str, Any]: A dictionary containing the user_id and a message
        """
        result = await self.user_repository.get_user_round_preferences(email,round)
        return result

        
def get_user_service(user_repository: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(user_repository) 