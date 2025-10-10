import logging
import pytz
from datetime import datetime

from future_bridge.repositories.commonRepository import OTPValidatorRepo,CommonRepo
from future_bridge.schema.recommendationSchema import CollegeRecommendationGroupResponse
from future_bridge.schema.commonSchema import CollegeConfigurationRequest,RoundPreferencesRequest,CollegeRoundPrefrence
from future_bridge.repositories.paymentRepository import PaymentRepository


from future_bridge.utils.JWTTokenGenrator import create_jwt  

class OTPService:
    """
    Service layer for handling operations related to counsellor scheduling.
    It interfaces with the counsellorRepository for CRUD operations.
    """
    
    def __init__(self):
        self.otp_repo = OTPValidatorRepo()
        logging.info('OTP Service initialized.')
    
    def get_current_time(self) -> str:
        # Define the IST timezone
        ist_timezone = pytz.timezone("Asia/Kolkata")
        return datetime.now(ist_timezone).isoformat()
    async def validateUser(self, email:str, otp:str, user_type:str):
        validation_result = await self.otp_repo.validate_otp(email=email, otp=otp, user_type=user_type)
        
        if validation_result["isValidOtp"]:
            payload = {"email": email, "name":validation_result.get("name")}
            access_token = create_jwt(payload)
            
            return {
                "isValidOtp": True,
                "accessToken": access_token,
                "name": validation_result.get("name"),
                "profileIcon": validation_result.get("profileIcon")
            }
        
        return validation_result

def get_otp_service()->OTPService:
    return OTPService()


class CommonService:
    def __init__(self):
        self.common_repo = CommonRepo()
        self.payment_repository = PaymentRepository()

    async def store_college_config(self, college_config: CollegeConfigurationRequest,email:str):

        return await self.common_repo.store_college_config(college_config,email)

    async def get_college_config(self, email: str):
        return await self.common_repo.get_college_config(email)

    async def store_round_preferences(self, round_preferences: RoundPreferencesRequest,email:str):
        return await self.common_repo.store_round_preferences(round_preferences,email)

    async def get_round_preferences(self, round_no: int,email:str,exam_type:str):
        return await self.common_repo.get_round_preferences(round_no,email,exam_type)

    async def generate_recommendations(self, round_preferences: RoundPreferencesRequest,email:str):
        exam_type=round_preferences.exam_type
        category=round_preferences.category
        round_no=round_preferences.round_no
        gender=round_preferences.gender
        district=round_preferences.district
        branchs=round_preferences.branches
        locations=round_preferences.locations
        last_college_round_choice_code=round_preferences.last_college_round_choice_code
        score=round_preferences.score

        if last_college_round_choice_code:
            previous_year_cutoff=await self.common_repo.get_previous_year_cutoff(exam_type,category,round_no,last_college_round_choice_code)
            cutoff_data=await self.common_repo.get_cutoff_data(exam_type=exam_type,category=category,round_no=round_no,previous_year_cutoff_dict=previous_year_cutoff,
            branchs=branchs,locations=locations,gender=gender,district=district)

        else:
            cutoff_data=await self.common_repo.get_cutoff_data(exam_type=exam_type,category=category,round_no=round_no,branchs=branchs,locations=locations,gender=gender,district=district)


        if not cutoff_data or score<=0:
            college_recommendation=CollegeRecommendationGroupResponse(
                username=email,
                Dream=[],
                Reach=[],
                Match=[],
                Safety=[],
                Round=round_no, 
                is_payment=False,
                accept_payment=False
            )

            await self.common_repo.store_college_recommendations(college_recommendation,round_no,exam_type)   

            return college_recommendation


        results = []
        is_payment = await self.payment_repository.is_user_payment_successful(email,exam_type=exam_type)

        accept_payment = await self.payment_repository.get_accept_payment_from_config()
        for key in cutoff_data.keys():
            for doc in cutoff_data.get(key):
                try:
                    if key=="home_university_cutoff_data":
                        categories_list=[category,"L"+category[1:]]
                        level="Home University"
                    elif key=="other_university_cutoff_data":
                        categories_list=[category[:-1]+"O","L"+category[1:-1]+"O"]
                        level="Other than Home University"
                    else:
                        if category[-1]=="H":
                            categories_list=[category[:-1]+"S","L"+category[1:-1]+"S"]
                        else:
                            categories_list=[category]
                        level="State Level"
                    cutoff_val=doc.get(categories_list[0],0)
                    considered_category=categories_list[0]
                    if gender=="female":
                        if len(categories_list)>1:
                            f_open_cutoff=doc.get(categories_list[1],0)
                            if f_open_cutoff<cutoff_val and f_open_cutoff!=0:
                                cutoff_val=f_open_cutoff 
                                considered_category=categories_list[1]
                            elif cutoff_val==0 and f_open_cutoff>0:
                                considered_category=categories_list[1]
                                cutoff_val=f_open_cutoff


                    last_year_cutoff = float(cutoff_val)
                    percentile_diff = score - last_year_cutoff
                    admission_probability, probability_message = self._calculate_probability(percentile_diff, score)
                    result = {
                        "college": {
                            "College_Name":doc.get("College Name"),
                            "College_Code":doc.get("College Code"),
                            "Course_Name":doc.get("Course Name"),
                            "Course_Code":doc.get("Course Code"),
                            "Location":doc.get("City"),
                        },
                        "admission_probability": admission_probability,
                        "probability_message": probability_message,
                        "cet_percentile": score,
                        "category": considered_category+" - "+level,

                        "cutoff": float(last_year_cutoff)
                    }
                    results.append(result)
                except Exception as e:
                    logging.error(f"Error in service while fetching all cutoff data: {e}")
                    continue
            
        dream_all = sorted([r for r in results if 10 <= r["admission_probability"] < 50], key=lambda x: -x["cutoff"])
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
            username=email,
            Dream=dream,
            Reach=reach,
            Match=match,
            Safety=safety,
            is_payment=is_payment,
            accept_payment=accept_payment
        )
        await self.common_repo.store_college_recommendations(college_recommendation,round_no,exam_type)   


        return college_recommendation


    def _calculate_probability(self, percentile_diff: float, cet_percentile: float = None) -> tuple[int, str]:
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
        elif 0 <= percentile_diff < 0.5:
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
    
    async def get_recommendations(self, round_no: int,email:str,exam_type:str):
        recommendations=await self.common_repo.get_recommendations(round_no,email,exam_type)
        if recommendations:
            recommendations[0]["is_payment"]=await self.payment_repository.is_user_payment_successful(email,exam_type=exam_type)
        return recommendations

    async def search_college_by_name(self, college_name: str,exam_type:str):
        college=await self.common_repo.search_college_by_name(college_name,exam_type)
        if not college:
            raise ValueError("College not found")
        return college

    async def search_college_by_college_code(self, college_code: int,exam_type:str):
        college=await self.common_repo.search_college_by_college_code(college_code,exam_type)
        if not college:
            raise ValueError("College not found")
        return college

    async def search_college_by_choice_code(self, choice_code: str,exam_type:str):
        college=await self.common_repo.search_college_by_choice_code(choice_code,exam_type)
        if not college:
            raise ValueError("College not found")
        return college

    async def store_round_college_preference(self, payload: CollegeRoundPrefrence,email:str):
        await self.common_repo.store_round_college_preference(payload,email)
    
    async def get_round_college_preferences(self, email: str, exam_type: str, round_no: int):
        return await self.common_repo.get_round_college_preference(email, exam_type, round_no)
    

def get_common_service()->CommonService:
    return CommonService()


