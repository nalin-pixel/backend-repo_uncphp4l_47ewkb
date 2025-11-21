"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Phone unlock request schema used by the app
class UnlockRequest(BaseModel):
    """
    Unlock requests from the multistep form
    Collection name: "unlockrequest" (lowercase of class name)
    """
    brand: str = Field(..., description="Device brand, e.g., Apple, Samsung")
    model: str = Field(..., description="Device model name")
    issue: str = Field(..., description="Lock type or issue to resolve")
    imei: str = Field(..., min_length=8, max_length=20, description="IMEI or serial number")
    region: Optional[str] = Field(None, description="Carrier/region the device is locked to")
    name: str = Field(..., description="Customer full name")
    email: EmailStr = Field(..., description="Customer email for updates")
    notes: Optional[str] = Field(None, description="Additional context or instructions")
    status: Literal['new', 'in_progress', 'completed', 'failed'] = Field('new', description="Processing status")
