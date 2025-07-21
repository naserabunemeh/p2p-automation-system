from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any, Union, Literal
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

# Enums for status fields
class VendorStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"

class POStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"
    RECEIVED = "received"
    CANCELLED = "cancelled"

class InvoiceStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"
    OVERDUE = "overdue"

# PaymentStatus enum removed - now using Literal["approved", "sent", "failed"] in Payment model

# Helper functions
def utc_now() -> datetime:
    """Return current UTC datetime using timezone-aware objects"""
    return datetime.now(timezone.utc)

# Base Models
class BaseEntity(BaseModel):
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Vendor Models
class VendorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = "Net 30"
    status: VendorStatus = VendorStatus.ACTIVE

class VendorCreate(VendorBase):
    pass

class VendorUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = None
    status: Optional[VendorStatus] = None

class Vendor(VendorBase, BaseEntity):
    pass

# Purchase Order Models
class PurchaseOrderBase(BaseModel):
    vendor_id: str
    items: List[Dict[str, Union[str, float, int]]]
    total_amount: float = Field(..., gt=0)
    status: Literal["pending", "approved", "rejected"] = "pending"

class PurchaseOrderCreate(PurchaseOrderBase):
    pass

class PurchaseOrderUpdate(BaseModel):
    vendor_id: Optional[str] = None
    items: Optional[List[Dict[str, Union[str, float, int]]]] = None
    total_amount: Optional[float] = None
    status: Optional[Literal["pending", "approved", "rejected"]] = None

class PurchaseOrder(PurchaseOrderBase, BaseEntity):
    pass

# Invoice Models
class InvoiceLineItem(BaseModel):
    line_number: int
    po_line_reference: Optional[int] = None
    description: str
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)
    total_amount: Decimal

class InvoiceBase(BaseModel):
    vendor_id: str
    po_id: Optional[str] = None
    invoice_number: str = Field(..., min_length=1)
    invoice_date: datetime
    due_date: datetime
    line_items: List[InvoiceLineItem]
    subtotal: Decimal = Field(..., gt=0)
    tax_amount: Decimal = Field(..., ge=0)
    total_amount: Decimal = Field(..., gt=0)
    status: InvoiceStatus = InvoiceStatus.PENDING
    approved_by: Optional[str] = None
    notes: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    invoice_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    line_items: Optional[List[InvoiceLineItem]] = None
    subtotal: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    status: Optional[InvoiceStatus] = None
    approved_by: Optional[str] = None
    notes: Optional[str] = None

class Invoice(InvoiceBase, BaseEntity):
    pass

# Payment Models
class PaymentBase(BaseModel):
    invoice_id: str
    vendor_id: str
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    status: Literal["approved", "sent", "failed"] = "approved"
    approved_at: datetime = Field(default_factory=utc_now)
    xml_s3_key: Optional[str] = None
    json_s3_key: Optional[str] = None

class PaymentCreate(BaseModel):
    invoice_id: str
    vendor_id: str
    amount: float = Field(..., gt=0)
    currency: str = "USD"

class PaymentUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = None
    status: Optional[Literal["approved", "sent", "failed"]] = None
    xml_s3_key: Optional[str] = None
    json_s3_key: Optional[str] = None

class Payment(PaymentBase, BaseEntity):
    pass

# Response Models
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int 