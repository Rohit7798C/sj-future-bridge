import logging
import os
from future_bridge.repositories.paymentRepository import PaymentRepository
import razorpay
from future_bridge.models.razorPayModel import RazorPay
from future_bridge.utils.PaymentProcessor import PaymentProcessor 
from future_bridge.schema.paymentSchema import PaymentRequestbody

KEY = os.getenv('RAZOR_PAY_KEY')
SECRET = os.getenv('RAZOR_PAY_SECRET')

class PaymentService:
    
    def __init__(self) -> None:
        self.payment_repository = PaymentRepository()

# ---------------- main service functions ------------------

    async def initiatePayment(self, user: PaymentRequestbody, amount: float):
        try:
            username = user.email
            logging.info(f'Initiating payment for {username}')                  
            return await self.generateOrderId(user, None, amount)

        except Exception as e:
            logging.error(f'An error occurred: {e}')
            raise e

    async def verifyAndSavePaymentCredential(self, req_body: dict):
        username = req_body.get("username") or ""
        logging.info(f'Verifying and saving payment credentials for {username}')
        payment_details = PaymentProcessor().wait_for_payment_id(req_body.get('order_id'))
        if payment_details and payment_details.get('status') == "paid":
            payment_details['email']=req_body.get("email")
            payment_details['order_id']=req_body.get("order_id")
            save_response = await self.payment_repository.savePaymentDetails(payment_details)
            if save_response:
                return True, 'verified_and_saved'
            else:
                return False, 'save_failed'
        else:
            logging.info('Payment verification failed')
            order_id = req_body.get('order_id') or ""
            store_failed = await self.payment_repository.save_payment_details_failed(order_id=order_id)
            if store_failed:
                logging.info('Payment details saved as failed')
            else:
                logging.error('Failed to save payment status as failed')
            return False, 'unverified'
        
    async def dropPaymentDetails(self, username: str):
        username = username or ""
        logging.info(f'Dropping payment details for {username}')
        try:
            result = await self.payment_repository.dropPaymentDetails(username)
            return result
        except Exception as e:
            logging.error(f'An error occurred: {e}')
            raise e
            
    async def findByOrderId(self, order_id: str):
        logging.info(f'Fetching payment details for order ID: {order_id}')
        response = await self.payment_repository.findByOrderId(order_id)
        if response is None:
            raise ValueError ("Payment details not found")
        elif '_id' in response:
            response['_id'] = str(response['_id'])
        return response

# -------------------razor pay sdk use-----------------------

    async def generateOrderId(self, user: PaymentRequestbody, payment, amount: float):
        name = user.full_name
        contact = user.contact
        email = user.email
        
        if payment is None:
            client = razorpay.Client(auth=(KEY, SECRET))
            DATA = {"amount": amount*100, "currency": "INR"}
            response = client.order.create(data=DATA)
            payment = self.processPayment({
                'username': email,
                'payment_for': user.product_type,
                'contact': contact,
            }, response)
            result = await self.payment_repository.insertOrderDetails(payment)
            logging.info('Generated RazorPay Order ID')
        else:
            result = True

        return {
            'razorpay_key': KEY, 
            'order_id': payment.order_id if payment else None,
            'amount': payment.amount if payment else None, 
            'currency': payment.currency if payment else None, 
            'status': payment.status if payment else None,
            'username': payment.username if payment else name, 
            'contact': contact,
            'email': email
        } if result else {}
        
    def verifyPaymentDetails(self, req_body: dict):
        logging.info('Verifying payment details')
        client = razorpay.Client(auth=(KEY, SECRET))

        return client.utility.verify_payment_signature({
            'razorpay_order_id': req_body.get('order_id'),
            'razorpay_payment_id': req_body.get('razorpay_payment_id'),
            'razorpay_signature': req_body.get('razorpay_signature')
        })

# -----------------formatters-------------------------------------------------

    def processPayment(self, req_body:dict, response):
        payment = RazorPay(
            username=req_body.get('username') or "",
            payment_for=req_body.get('payment_for'),
            contact=req_body.get('contact'),
            order_id=response.get('id') or response.get('order_id'),
            order_id_created_at=response.get('created_at') or response.get('order_id_created_at'),
            amount=response.get('amount'),
            currency=response.get('currency'),
            status=response.get('status'),
            razorpay_payment_id=response.get('razorpay_payment_id'),
            razorpay_signature=response.get('razorpay_signature'),
            payment_completed_at=response.get('Payment_success_timestamp') or response.get('payment_completed_at')
        )
        
        return payment


def get_payment_service() -> PaymentService:
    return PaymentService()