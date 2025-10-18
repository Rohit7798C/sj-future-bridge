import csv
import io
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, UploadFile
from future_bridge.config.config import Settings
from future_bridge.models.supportModel import Support, TicketStatus
from future_bridge.repositories.supportRepository import SupportRepository, get_support_repository
from typing import Dict, Any, List, Optional
from future_bridge.schema.supportSchema import SupportRequest
from azure.storage.blob.aio import BlobServiceClient

from future_bridge.utils.sendEmail import MicrosoftEmailService

# Define IST timezone (UTC +5:30)
IST = timezone(timedelta(hours=5, minutes=30))

class SupportService:
    """
    Service layer for handling support ticket operations.

    Handles ticket creation, blob uploads, email notifications,
    and business logic before repository persistence.
    """
    def __init__(self, support_repository: SupportRepository):
        self.support_repository = support_repository
        self.blob_service_client = BlobServiceClient.from_connection_string(Settings.CONNECTION_STRING)
        self.container_name = Settings.AZURE_BLOB_CONTAINER
        self.email_service = MicrosoftEmailService()

    async def upload_to_blob(self, filesuname: str, data: bytes) -> str:
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
                <p><b>Ticket ID:</b> {ticket_data.ticket_id}</p>
                <p><b>Details:</b> {ticket_data.details}</p>
                <p><b>Ticket Created At:</b> {created_at_str}</p>
                <p>If you have any further questions, you can reply to this email or contact support at <a href="mailto:support@skilljourney.in">support@skilljourney.in</a>.</p>
                <p>We will get back to you shortly.</p>
                <p>Sincerely,<br>The SkillJourney Team</p>
            </body>
            </html>
        """
        send_user_ticket_payload = {
            "user_email": ticket_data.username,
            "sender_email": "support@skilljourney.in",
            "cc_recipients": ["support@skilljourney.in"],
            "subject": f"Ticket ID: {ticket_data.ticket_id} | Your Support Ticket Details",
            "body_type": "HTML",
            "body": HTML_TEMPLATE,
        }

        logging.info(f"Sending ticket email to {ticket_data.username} and support...")
        response = MicrosoftEmailService().process_request(send_user_ticket_payload)
        logging.info(f"Email response: {response}")

    async def get_all_tickets(self, status: Optional[str], sort: str, page: int, limit: int):
        """
        Retrieve all support tickets with optional filters, sorting, and pagination.

        Args:
            status (str, optional): Ticket status filter.
            sort (str): Sorting field and direction (e.g., "created_at:desc").
            page (int): Current page number.
            limit (int): Number of tickets per page.

        Returns:
            dict: Paginated ticket list and metadata.
        """
        return await self.support_repository.get_all_tickets(status, sort, page, limit)
    
    async def get_ticket_by_id(self, ticket_id: str):
        """
        Service layer to fetch a single ticket by ticket_id.
        """
        return await self.support_repository.get_ticket_by_id(ticket_id)

    async def export_tickets_as_csv(self, status: Optional[str], ticket_ids: Optional[List[str]]):
        """
        Generate a CSV output for support tickets based on filters.

        Args:
            status (Optional[str]): Filter tickets by status.
            ticket_ids (Optional[List[str]]): Specific ticket IDs to export.

        Returns:
            io.StringIO: In-memory CSV file stream.
        """
        try:
            tickets = await self.support_repository.get_tickets_for_export(status, ticket_ids)

            if not tickets:
                raise HTTPException(status_code=404, detail="No tickets found for export")

            # Prepare CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Ticket ID", "Username", "Name", "Status", "Created At", "Is Paid", "Product Type"])

            for t in tickets:
                writer.writerow([
                    t.get("ticket_id", ""),
                    t.get("username", ""),
                    t.get("name", ""),
                    t.get("status", ""),
                    t.get("created_at", ""),
                    t.get("is_paid", ""),
                    t.get("product_type", "")
                ])

            output.seek(0)
            return output

        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Error generating CSV in SupportService: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error generating CSV: {e}")


    async def get_tickets_for_export(self, status: Optional[str], ticket_ids: Optional[List[str]]):
        """
        Fetch support tickets for CSV export (internal use).
        """
        try:
            return await self.support_repository.get_tickets_for_export(status, ticket_ids)
        except Exception as e:
            logging.error(f"Error in SupportService.get_tickets_for_export: {e}", exc_info=True)
            raise

    async def perform_bulk_action(self, action: str, ticket_ids: List[str]):
        return await self.support_repository.perform_bulk_action(action, ticket_ids)

    async def get_support_metrics(self):
        return await self.support_repository.get_support_metrics()
        

    
    # Adding comment on the Ticket
    async def add_comment(self, user_email: str, ticket_id: str, comment: str, attachments: Optional[List[str]] = None):
        """
        Add a comment to a ticket.
        """
        # Call repository function
        updated_ticket = await self.support_repository.add_comment_to_ticket(user_email, ticket_id, comment, attachments)

        # Send email to admin about user's comment
        # await self.send_email_to_admin(Support(**updated_ticket["ticket"]), subject_prefix="Comment Added", comment=comment)

        # New code added for above line
        await self._notify_after_comment(updated_ticket.get("ticket"), subject_prefix="Comment Added", comment=comment, actor="user")

        return updated_ticket

    # Adding a method to comment by admin
    async def add_comment_by_admin(self, admin_email: str, ticket_id: str, comment: str):
        """
        Admin adds a comment to a specific ticket.
        """
        # Call repository function for admin comment
        updated_ticket = await self.support_repository.add_comment_to_ticket_by_admin(admin_email, ticket_id, comment)


        await self._notify_after_comment(updated_ticket.get("ticket"), subject_prefix="Support Comment", comment=comment, actor="support", actor_email=admin_email)

        return updated_ticket

    async def _notify_after_comment(self, ticket: Optional[dict], subject_prefix: str, comment: Optional[str] = None, actor: str = "user", actor_email: Optional[str] = None):
        """
        Unified notification helper for comments.
        - ticket: the ticket dict returned from repository (not a Support model)
        - subject_prefix: short prefix like "Comment Added" or "Support Comment"
        - comment: comment text (optional)
        - actor: "user" or "support" (used for wording)
        - actor_email: the email of the actor who added the comment (optional)
        """
        if not ticket:
            logging.warning("No ticket data available for notification.")
            return

        # Compose email to admin/support
        # If actor is user -> notify support; if actor is support -> notify ticket owner
        ticket_model = None
        if isinstance(ticket, Support):
            ticket_model = ticket
        elif isinstance(ticket, dict):
            try:
                ticket_model = Support(**ticket)
            except Exception:
                logging.warning("Ticket dict could not be converted to Support model directly. Attempting to fetch full ticket from DB.")
                ticket_id = ticket.get("ticket_id") or ticket.get("_id")
                if ticket_id:
                    try:
                        full_ticket = await self.get_ticket_by_id(ticket_id)
                        if full_ticket:
                            try:
                                ticket_model = Support(**full_ticket)
                            except Exception as e:
                                logging.warning(f"Failed to convert fetched ticket to Support model: {e}")
                    except Exception as e:
                        logging.warning(f"Error fetching full ticket from DB: {e}")

        if not ticket_model:
            logging.warning("No valid ticket data available to send notifications; skipping emails.")
            return
    
        if actor == "user":
            # 1️⃣ User added a comment → notify support/admin
            await self.send_email_to_admin(ticket_model, subject_prefix=subject_prefix, comment=comment)

            # 2️⃣ Also notify the user (confirmation)
            await self.send_email_to_user(ticket_model, subject_prefix=subject_prefix, comment=comment)        

        elif actor == "support":
        # 1️⃣ Admin added a comment → notify user
            await self.send_email_to_user(ticket_model, subject_prefix=subject_prefix, comment=comment)

        # 2️⃣ Also notify admin (copy confirmation)
            await self.send_email_to_admin(ticket_model, subject_prefix=subject_prefix, comment=comment)

        logging.info(f"Notification emails sent successfully after comment addition by {actor}.")



    # sending an email to the Admin
    async def send_email_to_admin(self, ticket_data: Support, subject_prefix: str, comment: str = None):
        """
        Send email to admin(s) when a ticket is created or a comment is added.
        """
        admin_emails = ["support@skilljourney.in"]  # List of admin emails
        if not admin_emails:
            return

        created_at = ticket_data.created_at
        # created_at = ticket_data.get("created_at") if isinstance(ticket_data, dict) else ticket_data.created_at

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=IST)
        else:
            created_at = created_at.astimezone(IST)

        created_at_str = created_at.strftime("%Y-%m-%d %I:%M:%S %p IST")
        
        comment_text = f"<p><b>Comment:</b> {comment}</p>" if comment else ""
        
        HTML_TEMPLATE = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"></head>
            <body>
                <p>Dear Admin,</p>
                <p>A ticket has been <strong>{subject_prefix}</strong>.</p>
                <p><b>Ticket Details:</b> {ticket_data.details}</p>
                {comment_text}
                <p><b>Created At:</b> {created_at_str}</p>
                <p>From: {ticket_data.name or 'User'} ({ticket_data.username})</p>
                <p>Sincerely,<br>The SkillJourney Team</p>
            </body>
            </html>
        """

        for admin_email in admin_emails:
            payload = {
                "user_email": admin_email,
                "to_recipients": [admin_email],
                "sender_email": "support@skilljourney.in",
                "subject": f"{subject_prefix} - Ticket Notification",
                "body_type": "HTML",
                "body": HTML_TEMPLATE,
            }
            logging.info(f"Sending email to admin: {admin_email}")
            self.email_service.process_request(payload)


    async def send_email_to_user(self, ticket_data: Support, subject_prefix: str, comment: str = None):
        """
        Send email to the ticket owner (user) when support/admin adds a comment.
        Accepts a Support model.
        """
        user_email = ticket_data.username
        if not user_email:
            logging.warning("No user email provided; skipping user notification.")
            return

        created_at = ticket_data.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=IST)
        else:
            created_at = created_at.astimezone(IST)

        created_at_str = created_at.strftime("%Y-%m-%d %I:%M:%S %p IST")
        comment_text = f"<p><b>Comment:</b> {comment}</p>" if comment else ""

        HTML_TEMPLATE = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"></head>
            <body>
                <p>Dear {ticket_data.name or 'User'},</p>
                <p>{subject_prefix} on your ticket.</p>
                {comment_text}
                <p><b>Ticket Details:</b> {ticket_data.details}</p>
                <p><b>Created At:</b> {created_at_str}</p>
                <p>Sincerely,<br>The SkillJourney Team</p>
            </body>
            </html>
        """

        payload = {
            "user_email": user_email,
            "to_recipients": [user_email],
            "sender_email": "support@skilljourney.in",
            "subject": f"{subject_prefix} on Your Ticket - {ticket_data.ticket_id}",
            "body_type": "HTML",
            "body": HTML_TEMPLATE
        }

        logging.info(f"Sending comment notification to user: {user_email} with payload: { {k:v for k,v in payload.items() if k!='body'} }")
        resp = self.email_service.process_request(payload)
        logging.info(f"Email service response for user notification: {resp}")

    # Simple service layer function
    # It calls the repository (supportRepository.py) to interact with MongoDB.
    # Keeps business logic clean and reusable.
    async def get_user_tickets(self, user_email: str):
        """
        Retrieve all tickets for a given user.
        """
        tickets = await self.support_repository.get_user_tickets(user_email)
        return tickets
    


    async def validate_and_upload_files(self, files: List[UploadFile], max_size_mb: int = 20, max_files: int = 2):
        """
        Validate file extensions, size, and upload to Azure Blob Storage.
        Returns a list of blob IDs.
        """
        ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png", "mp4", "mov", "avi"}

        if files and len(files) > max_files:
            raise ValueError(f"Max {max_files} attachments allowed.")

        blob_ids = []
        for file in files:
            ext = file.filename.split(".")[-1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise ValueError(f"Invalid file type: {file.filename}. Allowed: {ALLOWED_EXTENSIONS}")

            contents = await file.read()
            if len(contents) > max_size_mb * 1024 * 1024:
                raise ValueError(f"{file.filename} exceeds {max_size_mb}MB limit.")

            blob_id = await self.upload_to_blob(file.filename, contents)
            blob_ids.append(blob_id)

        return blob_ids

def get_support_service(support_repository: SupportRepository = Depends(get_support_repository)) -> SupportService:
    return SupportService(support_repository) 
