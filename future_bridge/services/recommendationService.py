from future_bridge.repositories.recommendationRepository import RecommendationRepository
from future_bridge.schema.recommendationSchema import RecommendationRequest

class RecommendationService:
    def __init__(self):
        self.recommendation_repository = RecommendationRepository()

    async def generate_recommendation(self, request_data: RecommendationRequest):
        result = await self.recommendation_repository.store_recommendation(request_data)
        return result

    async def get_latest_recommendation_by_email(self, email: str):
        return await self.recommendation_repository.get_latest_recommendation_by_email(email)

def recommendation_service() -> RecommendationService:
    return RecommendationService() 