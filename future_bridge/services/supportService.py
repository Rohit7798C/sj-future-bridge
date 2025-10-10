import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import Depends
from future_bridge.config.config import Settings
from future_bridge.models.supportModel import Support
from future_bridge.repositories.supportRepository import SupportRepository, get_support_repository
from typing import Dict, Any
from future_bridge.schema.supportSchema import SupportRequest
from azure.storage.blob.aio import BlobServiceClient

from future_bridge.utils.sendEmail import MicrosoftEmailService

# Define IST timezone (UTC +5:30)
IST = timezone(timedelta(hours=5, minutes=30))

class SupportService:
    def __init__(self, support_repository: SupportRepository):
        self.support_repository = support_repository
        self.blob_service_client = BlobServiceClient.from_connection_string(Settings.CONNECTION_STRING)
        self.container_name = Settings.AZURE_BLOB_CONTAINER

    async def upload_to_blob(self, filename: str, data: bytes) -> str:
        """
        Upload a file to Azure Blob Storage and return the blob URL.
        """
        ext = os.path.splitext(filename)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=unique_name)
        await blob_client.upload_blob(data, overwrite=True)
        return blob_client.url

    async def store_user_tickets(self, support_request: SupportRequest, browser_info: str, files: list) -> Dict[str, Any]:
        """
        Store user tickets in the database
        
        Args:
            support_request: Pydantic model containing support request data
            browser_info: Information about the user's browser/system
            files: List of uploaded file URLs or names
        Returns:
            Dict[str, Any]: A dictionary containing the stored ticket info and status
        """
        # Initialize Feedback model
        user_ticket = Support(**support_request.model_dump(), browser_info = browser_info, attachments = files)
        
        # Store new feedback
        inserted_ticket = await self.support_repository.store_user_tickets(user_ticket)

        # Send confirmation email
        await self.send_ticket_copy(user_ticket)

        return inserted_ticket
    
    async def send_ticket_copy(self, ticket_data: Support):
        """
        Send a copy of the ticket to the user's email.
        """
        # Convert ticket time to IST if not already timezone-aware
        created_at = ticket_data.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=IST)
        else:
            created_at = created_at.astimezone(IST)

        # Format IST datetime nicely
        created_at_str = created_at.strftime("%Y-%m-%d %I:%M:%S %p IST")
        HTML_TEMPLATE = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"></head>
            <body>
                <p>Dear {ticket_data.name or 'User'},</p>
                <p>Thank you for contacting support. Your ticket has been created and is currently <strong>Open</strong>.</p>
                <p><b>Details:</b> {ticket_data.details}</p>
                <p><b>Ticket Created At:</b> {created_at_str}</p>
                <p>We will get back to you shortly.</p>
                <p>Sincerely,<br>The SkillJourney Team</p>
            </body>
            </html>
        """
        send_user_ticket_payload = {
            "user_email": ticket_data.username,
            "sender_email": "support@skilljourney.in",
            "subject": "Your Support Ticket Details",
            "body_type": "HTML",
            "body": HTML_TEMPLATE,
        }

        logging.info("Sending ticket email to user...")
        response = MicrosoftEmailService().process_request(send_user_ticket_payload)
        logging.info(f"Email response: {response}")
        
def get_support_service(support_repository: SupportRepository = Depends(get_support_repository)) -> SupportService:
    return SupportService(support_repository) 