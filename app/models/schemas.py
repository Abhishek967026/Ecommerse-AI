"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# ---- Product Schemas ----

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(gt=0)
    category: str
    brand: Optional[str] = None
    stock: int = Field(ge=0, default=0)
    image_url: Optional[str] = None
    rating: float = Field(ge=0, le=5, default=0.0)
    review_count: int = Field(ge=0, default=0)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    category: Optional[str] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---- Order Schemas ----

class OrderCreate(BaseModel):
    product_id: int
    customer_name: str = Field(min_length=2)
    customer_email: str
    quantity: int = Field(gt=0, default=1)
    shipping_address: Optional[str] = None
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    customer_name: str
    customer_email: str
    quantity: int
    total_price: float
    status: str
    shipping_address: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class OrderCancelRequest(BaseModel):
    reason: Optional[str] = "Customer requested cancellation"


# ---- Chat Schemas ----

class ChatMessage(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: Optional[str] = None
    customer_name: Optional[str] = "Guest"
    customer_email: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    agent_used: Optional[str] = None
    products_found: Optional[list] = None
    action_taken: Optional[str] = None
    trace_url: Optional[str] = None
