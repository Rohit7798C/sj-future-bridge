from datetime import datetime, timedelta, timezone
import logging
from future_bridge.models.supportModel import Support
from future_bridge.utils.db import get_db
from future_bridge.config.config import settings
from typing import Dict, Any

# Define IST timezone (UTC +5:30)
IST = timezone(timedelta(hours=5, minutes=30))
class SupportRepository:

    async def store_user_tickets(self, user_ticket: Support) -> Dict[str, Any]:
        """
        Store user ticket data in the FB_DATABASE support_issues collection
        Before storing, determine if the user has a paid record in user_payment.
        A payment is valid if:
            - status == 'paid'
            - payment_for == 'future-bridge'
            - payment_completed_at <= 1 year ago
        """
        try:
            # Get database connection to FB_DATABASE
            db = await get_db()

            # Check user payment status in user_payment collection
            payment_collection = db[settings.USER_PAYMENT_COLLECTION]
            payment_cursor = payment_collection.find(
                {
                    "username": user_ticket.username,
                    "payment_for": "future-bridge",
                    "status": "paid"
                }
            ).sort("payment_completed_at", -1)  # sort newest first

            payments = await payment_cursor.to_list(length=1)

            # Default to unpaid
            is_paid = False

            # Validate record exists and is within 1 year
            if payments:
                payment = payments[0]
                completed_at = payment.get("payment_completed_at")

                if completed_at:
                    # Convert to datetime if stored as string
                    if isinstance(completed_at, str):
                        completed_at = datetime.fromisoformat(completed_at)

                    # Ensure timezone awareness (convert to IST)
                    if completed_at.tzinfo is None:
                        completed_at = completed_at.replace(tzinfo=IST)

                    # Current IST time (aware)
                    now_ist = datetime.now(IST)

                    # Subtract aware datetimes
                    if now_ist - completed_at < timedelta(days=365):
                        is_paid = True

            user_ticket.is_paid = is_paid

            # Convert model to dict for insertion
            user_ticket_dict = user_ticket.model_dump()

            support_collection = db[settings.SUPPORT_ISSUES_COLLECTION]

            # Insert the document
            result = await support_collection.insert_one(user_ticket_dict)
            
            if not result.acknowledged:
                raise Exception("Failed to store user ticket data")
            
            # Retrieve the inserted document to return full data
            inserted_doc = await support_collection.find_one({"_id": result.inserted_id})
            if inserted_doc:
                # Convert ObjectId to string for JSON serialization
                inserted_doc["_id"] = str(inserted_doc["_id"])

            logging.info(f"User ticket stored for {user_ticket.username}, paid={is_paid}")
            return inserted_doc
            
        except ValueError as e:
            raise
        except Exception as e:
            logging.error(f"Error storing user ticket for {user_ticket.username}: {str(e)}", exc_info=True)
            raise Exception(f"Failed to store user ticket: {str(e)}")
    
def get_support_repository() -> SupportRepository:
    return SupportRepository() 