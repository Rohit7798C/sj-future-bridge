from pydantic import BaseModel, Field
from typing import Optional

class RazorPay(BaseModel):
    """
    Data model representing payment information for a user using Razorpay.
    """
    username: str
    payment_for: Optional[str] = None
    contact: Optional[int] = None
    order_id: Optional[str] = None
    order_id_created_at: Optional[int] = None
    payment_completed_at: Optional[str] = None
    amount: Optional[float] = Field(gt=0, default=0)
    currency: Optional[str] = None
    status: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None

    def __str__(self) -> str:
        return self.username
