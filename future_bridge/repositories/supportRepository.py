import asyncio
from datetime import datetime, timedelta, timezone
import logging

from pymongo import ReturnDocument
from future_bridge.models.supportModel import BulkAction, Support, TicketStatus
from future_bridge.utils.db import get_db
from future_bridge.config.config import settings
from typing import Dict, Any, List, Optional
from pydantic import EmailStr

# Define IST timezone (UTC +5:30)
IST = timezone(timedelta(hours=5, minutes=30))
class SupportRepository:
    """
    Repository layer for interacting with MongoDB `support_issues` collection.

    Performs CRUD operations and supports ticket metrics and exports.
    """
    
    @staticmethod
    async def generate_ticket_id(db) -> str:
        """
        Generate a unique, sequential ticket ID with prefix FB-XXXXX.
        Uses an atomic counter in MongoDB to ensure uniqueness.
        """
        counter_collection = db["ticket_counters"]
        result = await counter_collection.find_one_and_update(
            {"_id": "support_ticket"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        seq_num = result.get("seq", 1)
        return f"FB-{seq_num:05d}"

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
            user_ticket.is_paid = False

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
                        user_ticket.is_paid = True

            # Generate ticket ID
            user_ticket.ticket_id = await SupportRepository.generate_ticket_id(db)

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

            logging.info(f"User ticket {user_ticket.ticket_id} stored for {user_ticket.username}")
            return inserted_doc
            
        except ValueError as e:
            raise
        except Exception as e:
            logging.error(f"Error storing user ticket for {user_ticket.username}: {str(e)}", exc_info=True)
            raise Exception(f"Failed to store user ticket: {str(e)}")
        
    async def get_all_tickets(self, status: Optional[str], sort: str, page: int, limit: int):
        db = await get_db()
        collection = db[settings.SUPPORT_ISSUES_COLLECTION]
        query = {}
        if status:
            query["status"] = status

        # Sorting
        sort_field, sort_dir = sort.split(":")
        sort_order = -1 if sort_dir.lower() == "desc" else 1

        cursor = collection.find(query).sort(sort_field, sort_order).skip((page - 1) * limit).limit(limit)
        tickets = await cursor.to_list(length=limit)
        for t in tickets:
            t["_id"] = str(t["_id"])
        total = await collection.count_documents(query)
        return {"total": total, "page": page, "limit": limit, "tickets": tickets}

    async def get_ticket_by_id(self, ticket_id: str):
        """
        Fetch a single support ticket by its unique ticket_id.
        Ignore documents without ticket_id.
        """
        try:
            db = await get_db()
            collection = db[settings.SUPPORT_ISSUES_COLLECTION]

            # Fetch only tickets with a ticket_id
            ticket = await collection.find_one({
                "ticket_id": ticket_id
            })
            if ticket:
                # Convert MongoDB ObjectId to string to avoid Pydantic serialization issues
                ticket["_id"] = str(ticket["_id"])
            return ticket

        except Exception as e:
            logging.error(f"Error fetching ticket by ticket_id {ticket_id}: {e}", exc_info=True)
            raise

    async def get_tickets_for_export(self, status: Optional[str], ticket_ids: Optional[List[str]]) -> List[dict]:
        """
        Fetch support tickets from the database for CSV export using ticket_id.

        Args:
            status (Optional[str]): Filter by ticket status (case-insensitive).
            ticket_ids (Optional[List[str]]): List of specific ticket IDs.

        Returns:
            list: List of ticket documents.
        """
        try:
            db = await get_db()
            collection = db[settings.SUPPORT_ISSUES_COLLECTION]
            query = {}

            # Status filter
            if status:
                query["status"] = {"$regex": f"^{status}$", "$options": "i"}

            # Ticket IDs filter
            if ticket_ids:
                query["ticket_id"] = {"$in": ticket_ids}

            logging.info(f"Export query: {query}")

            tickets = await collection.find(query).to_list(None)
            return tickets or []

        except Exception as e:
            logging.error(f"Error in SupportRepository.get_tickets_for_export: {e}", exc_info=True)
            raise

    async def perform_bulk_action(self, action: str, ticket_ids: List[str]):
        """
        Perform bulk actions (delete, close, mark_paid) on tickets using ticket_id.
        Ignores documents without a ticket_id.
        """
        try:
            db = await get_db()
            collection = db[settings.SUPPORT_ISSUES_COLLECTION]

            # Filter only documents with ticket_id
            filter_query = {
                "ticket_id": {"$in": ticket_ids, "$exists": True, "$ne": ""}
            }

            if action == BulkAction.CLOSE:
                update_data = {"$set": {"status": "Closed"}}
            elif action == BulkAction.MARK_PAID:
                update_data = {"$set": {"is_paid": True}}
            elif action == BulkAction.DELETE:
                result = await collection.delete_many(filter_query)
                return {"deleted_count": result.deleted_count}
            else:
                raise ValueError(f"Unsupported bulk action: {action}")

            result = await collection.update_many(filter_query, update_data)
            return {"modified_count": result.modified_count}

        except ValueError as ve:
            logging.warning(f"Invalid bulk action: {ve}")
            raise
        except Exception as e:
            logging.error(f"Error performing bulk action {action}: {e}", exc_info=True)
            raise

    async def get_support_metrics(self):
        db = await get_db()
        collection = db[settings.SUPPORT_ISSUES_COLLECTION]

        # Tasks for concurrent execution
        tasks = [
            collection.count_documents({}),  # Total tickets
            collection.count_documents({"is_paid": True})  # Paid tickets
        ]

        # Count per status from TicketStatus enum
        for status in TicketStatus:
            tasks.append(collection.count_documents({"status": status.value}))

        results = await asyncio.gather(*tasks)

        metrics = {
            "total_tickets": results[0],
            "paid_tickets": results[1]
        }

        # Map status counts dynamically
        for idx, status in enumerate(TicketStatus, start=2):
            metrics[f"{status.name.lower()}_tickets"] = results[idx]

        return metrics
    

    # Connects to MongoDB using existing get_db().
    # Finds all documents in support_issues where username == user_email.
    # Sorts by created_at (latest first).
    # Converts _id from ObjectId to string (for JSON safety).
    # Returns list of tickets to the service layer.
    
    async def get_user_tickets(self, user_email: str):
        """
        Retrieve all support tickets for a given user from the database.
        """
        try:
            db = await get_db()
            support_collection = db[settings.SUPPORT_ISSUES_COLLECTION]

            # Fetch all tickets for this user
            cursor = support_collection.find({"username": user_email},{"_id":0}).sort("created_at", -1)
            tickets = await cursor.to_list(length=None)

            # Convert ObjectIds to strings for JSON
            # for ticket in tickets:
            #     ticket["_id"] = str(ticket["_id"])

            logging.info(f"Fetched {len(tickets)} ticket(s) for {user_email}")
            return tickets

        except Exception as e:
            logging.error(f"Error fetching tickets for {user_email}: {str(e)}", exc_info=True)
            raise Exception("Failed to fetch user tickets.")
        
    
    # Adding a Comment to the Ticket
    async def add_comment_to_ticket(self, user_email: EmailStr, ticket_id: str, comment: str, attachments: Optional[List[str]] = None):
        """
        Add a comment to a specific ticket by the user.
        Each comment is stored as a dict with user_email, comment text, and timestamp.
        """
        try:
            db = await get_db()
            support_collection = db[settings.SUPPORT_ISSUES_COLLECTION]
            
            filter_query = {"ticket_id": ticket_id, "username": user_email}
            
            comment_obj = {
                "timestamp": datetime.now(IST),
                "email": user_email,
                "user_type": "user",
                "comment": comment,
                "attachments": attachments or [],
            }
            
            updated_ticket = await support_collection.find_one_and_update(
                filter_query,
                {"$push": {"comments": comment_obj}},
                return_document=ReturnDocument.AFTER
            )

            if not updated_ticket:
                # No document matched — same error semantics as before
                raise ValueError("Ticket not found or you are not authorized to comment.")

            # Convert ObjectId to string for JSON (if you are returning _id)
            if "_id" in updated_ticket:
                updated_ticket["_id"] = str(updated_ticket["_id"])

            logging.info(f"Comment Added successfully to ticket {ticket_id}")

            return {
                "message": "Comment added successfully.",
                "data": comment_obj,
                "ticket": updated_ticket
            }

        except ValueError as ve:
            logging.error(f"Validation error: {str(ve)}")
            raise

        except Exception as e:
            logging.error(f"Error adding comment to ticket {ticket_id}: {str(e)}", exc_info=True)
            raise Exception("Failed to add comment to ticket.")
        
    
    # Adding a Comment to the Ticket by Admin
    async def add_comment_to_ticket_by_admin(self, admin_email: EmailStr, ticket_id: str, comment: str):
        """
        Add a comment to a specific ticket by an admin.
        Each comment is stored as a dict with admin_email, comment text, timestamp, and role.
        """
        try:
            db = await get_db()
            support_collection = db[settings.SUPPORT_ISSUES_COLLECTION]
            
            filter_query = {"ticket_id": ticket_id}
            
            comment_obj = {
                "timestamp": datetime.now(IST),
                "email": admin_email,
                "user_type": "admin",
                "comment": comment,
            }
            
            # Admin can update any ticket regardless of username
            updated_ticket = await support_collection.find_one_and_update(
                filter_query,
                {"$push": {"comments": comment_obj}},
                return_document=ReturnDocument.AFTER
            )

            if not updated_ticket:
                raise ValueError("Ticket not found. Admin cannot add comment.")

            if "_id" in updated_ticket:
                updated_ticket["_id"] = str(updated_ticket["_id"])

            logging.info(f"Admin comment added successfully to ticket {ticket_id}")

            return {
                "message": "Admin comment added successfully.",
                "data": comment_obj,
                "ticket": updated_ticket
            }

        except ValueError as ve:
            logging.error(f"Validation error: {str(ve)}")
            raise

        except Exception as e:
            logging.error(f"Error adding admin comment to ticket {ticket_id}: {str(e)}", exc_info=True)
            raise Exception("Failed to add admin comment to ticket.")
    
def get_support_repository() -> SupportRepository:
    return SupportRepository() 
