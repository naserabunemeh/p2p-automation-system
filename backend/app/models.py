from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
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

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

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
class POLineItem(BaseModel):
    line_number: int
    description: str
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)
    total_amount: Decimal

class PurchaseOrderBase(BaseModel):
    vendor_id: str
    po_number: str = Field(..., min_length=1)
    description: Optional[str] = None
    line_items: List[POLineItem]
    total_amount: Decimal = Field(..., gt=0)
    status: POStatus = POStatus.DRAFT
    requested_by: str
    approved_by: Optional[str] = None
    delivery_date: Optional[datetime] = None

class PurchaseOrderCreate(PurchaseOrderBase):
    pass

class PurchaseOrderUpdate(BaseModel):
    vendor_id: Optional[str] = None
    description: Optional[str] = None
    line_items: Optional[List[POLineItem]] = None
    total_amount: Optional[Decimal] = None
    status: Optional[POStatus] = None
    approved_by: Optional[str] = None
    delivery_date: Optional[datetime] = None

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
    payment_amount: Decimal = Field(..., gt=0)
    payment_method: str = "ACH"
    payment_date: Optional[datetime] = None
    reference_number: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    processed_by: Optional[str] = None
    notes: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class PaymentUpdate(BaseModel):
    payment_amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    payment_date: Optional[datetime] = None
    reference_number: Optional[str] = None
    status: Optional[PaymentStatus] = None
    processed_by: Optional[str] = None
    notes: Optional[str] = None

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