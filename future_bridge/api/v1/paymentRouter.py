from fastapi import APIRouter, HTTPException, Depends
import logging

from future_bridge.config.messages import ErrorMessages, Success

from future_bridge.services.razorPayService import PaymentService, get_payment_service

from future_bridge.schema.paymentSchema import *
from future_bridge.schema.commonSchema import *

router = APIRouter()


@router.post("/payment/initiate", tags=["Payment"],response_model=ResponseSchema)
async def initiate_payment(
    request: PaymentRequestbody,
    payment_service: PaymentService = Depends(get_payment_service)
):
    """
    Initiate payment for a user.
    """
    logging.info("POST - /payment/initiate")
    try:
        amount = request.amount
        result = await payment_service.initiatePayment(request, amount)
        response = ResponseSchema(message=Success.SUCCESS_RAZORPAY_ORDERID, success=True, data=result)
        return response
    except Exception as e:
        logging.error(f"Error in initiating payment: {e}")
        raise HTTPException(status_code=500, detail={
            "error": ErrorMessages.ERROR_WHILE_FETCH,
            "technicalError": str(e)
        })

@router.put("/payment/verify", tags=["Payment"], response_model=ResponseSchema)
async def verify_and_save_payment_credential(
    request: VerifyPaymentRequestbody,
    payment_service: PaymentService = Depends(get_payment_service)
):
    """
    Verify and save payment credentials.
    """
    logging.info("PUT - /payment/verify")
    try:
        request_data = request.model_dump()
        response_val, msg = await payment_service.verifyAndSavePaymentCredential(request_data)
        if msg == "verified_and_saved" and response_val:
            result = ResponseSchema(message=Success.SUCCESS_RAZORPAY_VERIFY_SAVED, success=True, data={})
            return result
        elif msg == "unverified":
            result = ResponseSchema(message=ErrorMessages.ERROR_PAYMENT_DETAILS, success=False, data={})
            return result
        elif msg == "save_failed":
            result = ResponseSchema(message=ErrorMessages.ERROR_SAVE_PAYMENT_DETAILS, success=False, data={})
            return result
        else:
            result = ResponseSchema(message="Unexpected error occurred.", success=False, data={})
            return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error in verifying payment credentials: {e}")
        if str(e).startswith("Razorpay Signature Verification Failed"):
            raise HTTPException(status_code=406, detail={"error": ErrorMessages.ERROR_PAYMENT_DETAILS,"technicalError": str(e)})
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_WHILE_FETCH.format(error="Something went wrong. Please try again."),
                                                     "technicalError": str(e)})

@router.delete("/payment/delete", tags=["Payment"], response_model=ResponseSchema)
async def drop_payment_details(
    request: EmailSchema,
    payment_service: PaymentService = Depends(get_payment_service)
):
    """
    Drop payment details for a user.
    """
    logging.info("DELETE - /payment/delete")
    try:
        username = request.email  # If you want to use username, change EmailSchema to UsernameSchema
        result = await payment_service.dropPaymentDetails(username)
        if not result:
            result = ResponseSchema(message="Payment details not found", success=False, data={})
            return result
        response = ResponseSchema(message=Success.SUCCESS_DROP_PAYMENT_DETAILS, success=result, data=str(username))
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error in dropping payment details: {e}")
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_WHILE_DROP_PAYMENT_DETAILS,"technicalError": str(e)})

@router.post("/payment/info", tags=["Payment"], response_model=ResponseSchema)
async def payment_info_by_order_id(
    request: paymentOrderIdSchema,
    payment_service: PaymentService = Depends(get_payment_service)
):
    """
    Get payment info by order ID.
    """
    logging.info("GET - /payment/info")
    order_id = request.order_id
    if not order_id:
        raise HTTPException(status_code=400, detail={
            "error": ErrorMessages.ERROR_PARAMS_ORDERID,
            "technicalError": "Missing order_id parameter"
        })
    try:
        response_val = await payment_service.findByOrderId(order_id)
        result = ResponseSchema(message=Success.SUCCESS_PAYMENT_DETAILS_ORDERID, success=True, data=dict(response_val))
        return result
    except ValueError as e:
        result = ResponseSchema(message=f"Payment details not found for order ID: {order_id}", success=False, data={})
        return result
    except Exception as e:
        logging.error(f"Error in fetching payment info by order ID: {e}")
        raise HTTPException(status_code=500, detail={"error": ErrorMessages.ERROR_WHILE_FETCH,"technicalError": str(e)})
