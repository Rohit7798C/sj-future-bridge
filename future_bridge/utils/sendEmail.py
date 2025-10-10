import msal
import requests
from pydantic import BaseModel, ValidationError
import logging
import os
from typing import List, Optional
import random
from future_bridge.repositories.commonRepository import OTPValidatorRepo
from future_bridge.models.commonModel import OTPValidator

otp_validator=OTPValidatorRepo()
# Microsoft Graph API endpoint
GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
 
# Load environment variables for Azure App credentials
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
tenant_id = os.getenv('TENANT_ID')
EMAIL_SERVICE = os.getenv('EMAIL_SERVICE')

# Define the scope for Microsoft Graph API access
SCOPES = ['https://graph.microsoft.com/.default']
 
# Ensure required environment variables are set
if not all([client_id, client_secret, tenant_id]):
    logging.error("Missing Azure AD credentials. Check environment variables CLIENT_ID, CLIENT_SECRET, and TENANT_ID.")
    raise EnvironmentError("Azure AD credentials are not set.")
 
class EmailRequest(BaseModel):
    to_recipients: List[str]
    subject: str
    body: str
    body_type: Optional[str] = "Text"  # Can be "Text" or "HTML"
    cc_recipients: Optional[List[str]] = None
    bcc_recipients: Optional[List[str]] = None
    attachments: Optional[List[dict]] = None  # Attachment payloads if needed
 
class MicrosoftEmailService:
    def __init__(self):
        self.access_token = self.get_access_token()
    print(client_id,client_secret,tenant_id)
    
    def get_access_token(self) -> str:
        """
        Acquires an access token from Azure AD using client credentials (Client ID, Secret, and Tenant ID).
        """
        try:
            authority = f'https://login.microsoftonline.com/{tenant_id}'
            app = msal.ConfidentialClientApplication(
                client_id, authority=authority, client_credential=client_secret
            )
            token_response = app.acquire_token_for_client(SCOPES)
            print(token_response)

            if 'access_token' in token_response:
                return token_response['access_token']
            logging.error("Failed to acquire access token.")
            raise Exception('Could not acquire access token.')
        except Exception as e:
            logging.error(f"Error acquiring access token: {e}")
            raise
 
    def process_request(self, request_data: dict) -> dict:
        """
        Processes the incoming request data, validates it, and sends an email.
 
        Parameters:
            request_data (dict): The JSON data from the incoming HTTP request.
 
        Returns:
            dict: Success or failure message.
        """
        try:
            # Extract user and sender emails
            user_email = request_data.get('user_email')
            to_recipients = request_data.get('to_recipients', [user_email] if user_email else [])
            sender_email = request_data.get('sender_email', 'admin@skilljourney.in')  # Dynamic sender email with default

            # Ensure required fields are present
            if not to_recipients or not sender_email:
                logging.error("Missing to_recipients or sender_email in the request.")
                return {
                    "success": False,
                    "message": "Missing to_recipients or sender_email in the request."
                }
            
            # Determine the subject based on the environment
            subject = request_data.get('subject', 'No Subject')
            if EMAIL_SERVICE == 'Development':
                subject = f"Development: {subject}"

            # Validate and parse the rest of the request data into an EmailRequest object
            email_request = EmailRequest(
                to_recipients=to_recipients,  # Use the full list of recipients
                subject=subject,
                body=request_data.get('body', ''),
                body_type=request_data.get('body_type', 'Text'),
                cc_recipients=request_data.get('cc_recipients'),
                bcc_recipients=request_data.get('bcc_recipients'),
                attachments=request_data.get('attachments')
            )
            # Call the send_email method with the validated EmailRequest object
            return self.send_email(email_request, sender_email)
 
        except ValidationError as ve:
            logging.error(f"Validation error: {ve}")
            return {
                "success": False,
                "message": "Validation failed. Check required fields and data types.",
                "details": ve.errors()
            }
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return {
                "success": False,
                "message": "An unexpected error occurred during email processing."
            }
 
    def send_email(self, email_request: EmailRequest, sender_email: str) -> dict:
        """
        Sends an email using the Microsoft Graph API based on the provided EmailRequest data.
 
        Args:
            email_request (EmailRequest): The validated email request data.
            sender_email (str): The dynamic sender email address.
        """
        url = f"{GRAPH_API_ENDPOINT}/users/{sender_email}/sendMail"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
       
        email_payload = self.create_email_payload(email_request)
 
        try:
            response = requests.post(url, headers=headers, json=email_payload)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx, 5xx)
            logging.info(f"Email sent successfully to: {', '.join(email_request.to_recipients)}")
            return {"success": True, "message": f"Successfully sent email to {', '.join(email_request.to_recipients)}"}
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err} - Response: {response.json()}")
            return {"success": False, "message": f"Failed to send email. Reason: {response.json()}"}
        except Exception as err:
            logging.error(f"An unexpected error occurred: {err}")
            return {"success": False, "message": "An unexpected error occurred during email sending."}
 
    def create_email_payload(self, email_request: EmailRequest) -> dict:
        """
        Creates the email payload for the Microsoft Graph API request.
        """
        return {
            "message": {
                "subject": email_request.subject,
                "body": {
                    "contentType": email_request.body_type,
                    "content": email_request.body
                },
                "toRecipients": [{"emailAddress": {"address": email}} for email in email_request.to_recipients],
                "ccRecipients": [{"emailAddress": {"address": email}} for email in (email_request.cc_recipients or [])],
                "bccRecipients": [{"emailAddress": {"address": email}} for email in (email_request.bcc_recipients or [])],
                "attachments": email_request.attachments or []
            },
            "saveToSentItems": "true"
        }
 

    async def send_otp(self,email:str):
        otp = random.randint(100000, 999999)
        HTML_TEMPLATE="""
            <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Your OTP Code</title>
                </head>
                <body>
                    <p>Dear User,</p>
                    <p>Here is your One-Time Password (OTP): <strong>[OTP]</strong></p>
                    <p>Please use this code to complete your verification process.</p>
                    <p>If you did not request this OTP, please reach out to support@skilljourney.in.</p>
                    <p>Sincerely,<br>The SkillJourney Team</p>
                </body>
                </html>
        """.replace('[OTP]',str(otp))
        send_otp_payload = {
            "user_email": email,
            "sender_email": "admin@skilljourney.in",
            "subject": f"OTP for SkillJourney Login {str(otp)}",
            "body_type": "HTML",
            "body": HTML_TEMPLATE,  
        }
        email_response =self.process_request(send_otp_payload)
        otpData=OTPValidator(useremail = email,otp=otp)
        dataStored= await otp_validator.store_otp(otpData)
        logging.info(f'Otp Data Inserted {dataStored}')
        logging.info(f"Email Response {email_response}")
        return email_response
def get_microsoft_email_service() -> MicrosoftEmailService:
    return MicrosoftEmailService()


if __name__ == "__main__":
    # Example scenario: Sending a feedback, contact, or support email
    user_email = "user@example.com"  # Replace with the actual user's email
    sender_email = "parth.pardeshi@skilljourney.in"  # Replace with the actual sender's email
 
    try:
        email_service = MicrosoftEmailService()
        feedback_request = {
            "user_email": user_email,
            "sender_email": sender_email,
            "subject": "User Feedback Submission",
            "body": "This is a sample feedback message from the feedback form.",
            "body_type": "HTML",
            "cc_recipients": ["cc@example.com"],  # Optional
            "attachments": [{
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": "feedback.txt",
                "contentBytes": "VGVzdCBjb250ZW50",  # Base64-encoded content for "Test content"
                "contentType": "text/plain"
            }]
        }
        result = email_service.process_request(feedback_request)
        print(result)
    except Exception as e:
        logging.error(f"Failed during the feedback email sending process: {e}")





