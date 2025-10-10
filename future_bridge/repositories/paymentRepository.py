import logging
from future_bridge.utils.db import get_db
from future_bridge.config.config import settings
from future_bridge.models.razorPayModel import RazorPay

class PaymentRepository:
    async def findUserPaymentOrOrderStatus(self, username: str):
        """
        Finds a user's payment or order status by username.

        Args:
            username (str): The user's username to search for.

        Returns:
            dict: The document found in the collection, or None if not found.
        """
        db = await get_db()
        document = await db[settings.USER_PAYMENT_COLLECTION].find_one({"username": username})
        return document

    async def insertOrderDetails(self, payment: RazorPay):
        """
        Inserts order details into the collection.

        Args:
            payment (RazorPay): The payment details to insert.

        Returns:
            ObjectId: The ID of the inserted document.
        """
        db = await get_db()
        result = await db[settings.USER_PAYMENT_COLLECTION].insert_one(payment.__dict__)
        return result.inserted_id

    async def savePaymentDetails(self, payment: dict) -> bool:
        """
        Updates the payment details of an existing order.

        Args:
            payment (dict): The payment details to update.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        db = await get_db()
        query = {
            "username": payment.get('email'),
            "order_id": payment.get("order_id")
        }
        new_values = {
            "$set": {
                "status": "paid",
                "razorpay_payment_id": payment.get("razorpay_payment_id"),
                "amount": payment.get("amount"),
                "currency": payment.get("currency"),
                "created_at": payment.get("created_at"),
                "payment_completed_at": payment.get("Payment_success_timestamp"),
            }
        }
        logging.info('Saving payment details...')
        result = await db[settings.USER_PAYMENT_COLLECTION].update_one(query, new_values)
        logging.info(f"Update result: {result.raw_result}")
        return result.modified_count > 0

    async def dropPaymentDetails(self, username: str):
        """
        Deletes a user's payment details from the collection.

        Args:
            username (str): The username of the user whose payment details should be deleted.
        """
        logging.info("Dropping user payment details...")
        db = await get_db()
        document = await db[settings.USER_PAYMENT_COLLECTION].delete_one({"username": username})  
        return document.deleted_count > 0

    async def findByOrderId(self, order_id: str):
        """
        Finds payment details by order ID.

        Args:
            order_id (str): The order ID to search for.

        Returns:
            dict: The document found in the collection, or None if not found.
        """
        db = await get_db()
        document = await db[settings.USER_PAYMENT_COLLECTION].find_one({"order_id": order_id})
        logging.info(document)
        return document
    
    async def is_valid_order_id(self, order_id: str) -> bool:
        """
        Check if the given order_id exists in the MongoDB collection for payments.

        Args:
            order_id (str): The order ID to validate.

        Returns:
            bool: True if the order ID exists, False otherwise.
        """
        db = await get_db()
        result = await db[settings.USER_PAYMENT_COLLECTION].find_one({"order_id": order_id})
        return result is not None

    async def save_payment_details_failed(self, order_id: str) -> bool:
        """
        Update the payment status to 'failed' for the given order ID.

        Args:
            order_id (str): The order ID to update.
        """
        db = await get_db()
        query = {"order_id": order_id}
        new_values = {"$set": {"status": "failed"}}
        result = await db[settings.USER_PAYMENT_COLLECTION].update_one(query, new_values)
        return result.modified_count > 0

    async def is_user_payment_successful(self, username: str,diploma:bool=False,exam_type:str=None) -> bool:

        """
        Returns True if the user has any payment with status 'paid', otherwise False.
        """
        db = await get_db()
        if exam_type:
            query = {"username": username, "status": "paid","payment_for": f"future-bridge-admissionType-{exam_type}"}
            user_payment = await db[settings.USER_PAYMENT_COLLECTION].find_one(query)
            if user_payment:
                return True
            else:
                return False
        else:
            query = {"username": username, "status": "paid","payment_for": "future-bridge-dsy" if diploma else "future-bridge"}
            user_payment = await db[settings.USER_PAYMENT_COLLECTION].find_one(query)
            if user_payment:
                return True
            else:
                return False

    async def get_accept_payment_from_config(self) -> bool:
        """
        Fetches the 'accept_payment' boolean from the config collection.
        """
        db = await get_db()
        config_doc = await db[settings.CONFIG_COLLECTION].find_one({"accept_payment": {"$exists": True}})
        return bool(config_doc and config_doc.get("accept_payment"))