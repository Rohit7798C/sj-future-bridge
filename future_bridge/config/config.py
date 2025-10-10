import os
from dotenv import load_dotenv
import logging
 
 
load_dotenv()
 
class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Calling-Kosmos")
    DATABASE_URL: str = os.getenv("COSMO_URI")
    GENERATEDCAREERJOURNEY_URL: str = os.getenv('GENERATEDCAREERJOURNEY_URL')
    DATABASE = 'sj-future-bridge'
    CJ_DATABASE='career_journeys'
    USER_COLLECTION='user_info'
    USER_PAYMENT_COLLECTION='user_payment'
    CONFIG_COLLECTION='config'
    INSTIUTE_META_COLLECTION = 'institute_meta'
    USER_ROUND_COLLECTION= 'user_round_details'
    DEPARTMENT_META_COLLECTION = 'department_meta'  # New collection for CET cutoff data
    COLLEGE_CUTOFF_COLLECTION = 'College_cutoff'  # Verify this matches your MongoDB collection name
    DIPLOMA_COLLEGE_CUTOFF_COLLECTION="diploma_cutoff"
    USER_RECOMMENDATIONS_COLLECTION = 'user_recommendations'
    DIPLOMA_RECOMMENDATIONS_COLLECTION = 'diploma_recommendations'
    DIPLOMA_USER_CONFIG_COLLECTION = 'diploma_user_config'
    COLLEGE_CONFIG='college_config'
    RECOMMENDATIONS_COLLECTION = 'recommendations'
    PROVISIONAL_VACANT_SEAT_COLLECTION='provisional_vacant_seat_round'
    BCA_COLLEGE_CUTOFF_COLLECTION='BCA_MCA_Integrated_cutoff'
    BBA_COLLEGE_CUTOFF_COLLECTION='BBA_BMS_BBM_MBA_Integrated_cutoff'
    PHARMACY_COLLEGE_CUTOFF_COLLECTION='B_and_D_Pharmacy_cutoff'
    FEEDBACK_COLLECTION='user_feedback'
    SUPPORT_ISSUES_COLLECTION='support_issues'
    UNIVERSITY_MAPPING='university_mapping'
    COMMON_ROUND_PREFERENCES='common_round_preferences'
    ROUND_COLLEGE_PREFERENCE_COLLECTION='common_round_college_preferences'
    USER_ROUND_PREFERENCES='user_round_preferences'
    COMMON_RECOMMENDATIONS='common_recommendations'
    # Handle blob storage settings with defaults
    BLOB_STORAGE_ACCOUNT_NAME = os.getenv("BLOB_STORAGE_ACCOUNT_NAME", "")
    ACCOUNT_URL = f"https://{BLOB_STORAGE_ACCOUNT_NAME}.blob.core.windows.net" if BLOB_STORAGE_ACCOUNT_NAME else ""
    CONNECTION_STRING = os.getenv("BLOB_STORAGE_CONNECTION_STRING", "")
    AZURE_BLOB_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER", "")
    OTP_VALIDATOR='otp_validator'
    USERS_COLLECTION='user_info'
    CONUSELOR_INFO=''
    HR_INFO=''
    COLLEGE_ADMIN_COLLECTION=''

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
settings = Settings()