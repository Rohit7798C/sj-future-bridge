from pydantic import BaseModel, Field
from typing import Literal
from pydantic import EmailStr


class PaymentRequestbody(BaseModel):
    full_name: str
    email: EmailStr
    contact: int = Field(gt=1000000000, lt=9999999999)
    product_type: str
    amount: float = Field(gt=0)


class VerifyPaymentRequestbody(BaseModel):
    email: EmailStr
    order_id: str
