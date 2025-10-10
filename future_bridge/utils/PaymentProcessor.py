from datetime import datetime
import time
import logging
import os
import razorpay

from future_bridge.utils.sendEmail import MicrosoftEmailService

KEY = os.getenv('RAZOR_PAY_KEY')
SECRET = os.getenv('RAZOR_PAY_SECRET')

class PaymentProcessor:
    def __init__(self, timeout=10*60, interval=5):
        self.timeout = timeout
        self.interval = interval

    def get_payment_details_by_order_id(self, order_id: str):
        logging.info(f'fetching payment details for {order_id}')
        try:
            client = razorpay.Client(auth=(KEY, SECRET))
            return client.order.payments(order_id)
        except Exception as e:
            print(e)
            return None
        
    def get_payment_details_by_payment_id(self,payment_id:str):
        logging.info('fetching payment details')
        try:
            client = razorpay.Client(auth=(KEY, SECRET))

            return client.payment.fetch(payment_id)
        except Exception as e:
            print(e)
            return None


    def wait_for_payment_id(self, order_id):
        start_time = time.time()
        
        payment_response={"order_id":order_id}

        while True:
            payment_details = self.get_payment_details_by_order_id(order_id)
            if payment_details is None:
                return None
       
            # Check if we have the required value
            payment = payment_details.get('items')
            if payment and len(payment) > 0:
                for payment_data in payment:
                    if payment_data.get('status')=="captured" or payment_data.get('status')=="failed":
                        payment_response['razorpay_payment_id']=payment_data.get('id')
                        payment_response['status']="paid" if payment_data.get('status')=="captured" else payment_data.get('status')
                        payment_response['Payment_success_timestamp']= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        payment_response['created_at']=payment_data.get('created_at')
                        payment_response['currency']=payment_data.get('currency')
                        payment_response['amount']=payment_data.get('amount')
                logging.info(f'Returning Response {payment_response}')
                return payment_response

            # Check for timeout
            if time.time() - start_time > self.timeout:
                payment_response['razorpay_payment_id']=""
                payment_response['status']="failed"
                payment_response['Payment_success_timestamp']= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                payment_response['created_at']=""
                payment_response['currency']=""
                payment_response['amount']=""
                return payment_response

            # Wait before polling again
            time.sleep(self.interval)

def sendBypassEmail(username):
    try:
        premium_journey_template = {
        "user_email": username,
        "sender_email": "admin@skilljourney.in",
        "subject": "Thank you for choosing FutureBridge. ",
        "body": PREMIUM_JOURNEY_BYPASS_TEMPLATE.replace('$USERNAME$', username),
        "body_type": "HTML",
        "bcc_recipients": ["admin@skilljourney.in"]
        }
        email_response=MicrosoftEmailService().process_request(premium_journey_template)
        logging.info(f"Email Send to user- {username}- Response {(email_response)}")
    except Exception as e:
        logging.error(f"Email notification for Payment Response Failed {e}")

def sendEmail(username):
    try:
        premium_journey_template = {
        "user_email": username,
        "sender_email": "admin@skilljourney.in",
        "subject": "Thank you for your payment.",
        "body": PREMIUM_JOURNEY_TEMPLATE.replace('$USERNAME$', username),
        "body_type": "HTML",
        "bcc_recipients": ["admin@skilljourney.in"]
        }
        email_response=MicrosoftEmailService().process_request(premium_journey_template)
        logging.info(f"Email Send to user- {username}- Response {(email_response)}")
    except Exception as e:
        logging.error(f"Email notification for Payment Response Failed {e}")

PREMIUM_JOURNEY_TEMPLATE="""
<!DOCTYPE html>
    <html lang=\"en\">
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <title>College Recommendation Ready</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f9f9f9;
                margin: 0;
                padding: 20px;
            }
            .container {
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                padding: 20px;
                max-width: 600px;
                margin: auto;
            }
            .logo {
                text-align: center;
                margin-bottom: 20px;
            }
            .logo img {
                max-width: 150px; /* Adjust as necessary */
            }
            h1 {
                color: #333;
            }
            p {
                color: #555;
                line-height: 1.6;
            }
            .link {
                display: inline-block;
                margin-top: 15px;
                padding: 10px 15px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
            }
            .link:hover {
                background-color: #0056b3;
            }
            .footer {
                margin-top: 20px;
                font-size: 0.9em;
                color: #777;
            }
        </style>
    </head>
    <body>
        <div class=\"container\">
            
            <p>Dear $USERNAME$,</p>

            <p>Thank you for choosing FutureBridge. Your College Recommendation is being prepared.</p>

            <p>Your personalized college recommendation is currently being crafted. Please allow up to <b>48 hours</b> for its completion. As soon as your recommendation is ready, we will notify you via email.</p>

            <p>We are excited to help you on your academic journey.</p>

            <p>Sincerely,<br>The FutureBridge Team</p>
        </div>
    </body>
    </html>
"""

PREMIUM_JOURNEY_BYPASS_TEMPLATE="""
<!DOCTYPE html>
    <html lang=\"en\">
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <title>College Recommendation Ready</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f9f9f9;
                margin: 0;
                padding: 20px;
            }
            .container {
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                padding: 20px;
                max-width: 600px;
                margin: auto;
            }
            .logo {
                text-align: center;
                margin-bottom: 20px;
            }
            .logo img {
                max-width: 150px; /* Adjust as necessary */
            }
            h1 {
                color: #333;
            }
            p {
                color: #555;
                line-height: 1.6;
            }
            .link {
                display: inline-block;
                margin-top: 15px;
                padding: 10px 15px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
            }
            .link:hover {
                background-color: #0056b3;
            }
            .footer {
                margin-top: 20px;
                font-size: 0.9em;
                color: #777;
            }
        </style>
    </head>
    <body>
        <div class=\"container\">
            
            <p>Dear $USERNAME$,</p>

            <p>Thank you for choosing FutureBridge. Your College Recommendation is being prepared.</p>

            <p>Your personalized college recommendation is currently being crafted. Please allow up to <b>48 hours</b> for its completion. As soon as your recommendation is ready, we will notify you via email.</p>

            <p>We are excited to help you on your academic journey.</p>

            <p>Sincerely,<br>The FutureBridge Team</p>
        </div>
    </body>
    </html>
"""