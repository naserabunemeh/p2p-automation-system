"""
Pydantic Data Models for ERP-Lite P2P Automation System

This module defines all the data models used throughout the P2P automation system.
It uses Pydantic for data validation, serialization, and API documentation generation.
The models represent core business entities in the procure-to-pay process.

Key Features:
    - Type validation and serialization via Pydantic
    - Enum-based status management for consistency
    - Timestamp handling with timezone awareness
    - Field validation with appropriate constraints
    - API documentation integration through Pydantic

Business Entities:
    - Vendors: Supplier information and contact details
    - Purchase Orders: Procurement requests and approvals
    - Invoices: Billing documents with line items
    - Payments: Financial transaction records

Author: Development Team
Version: 1.0.0
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any, Union, Literal
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

# Status enumerations for business entities
class VendorStatus(str, Enum):
    """
    Enumeration of possible vendor status values.
    
    Attributes:
        ACTIVE: Vendor is active and can receive purchase orders
        INACTIVE: Vendor is temporarily inactive
        PENDING: Vendor setup is pending approval
        SUSPENDED: Vendor is suspended from transactions
    """
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"

class POStatus(str, Enum):
    """
    Enumeration of purchase order status values.
    
    Attributes:
        DRAFT: Purchase order is in draft state
        APPROVED: Purchase order has been approved
        SENT: Purchase order has been sent to vendor
        RECEIVED: Goods/services have been received
        CANCELLED: Purchase order has been cancelled
    """
    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"
    RECEIVED = "received"
    CANCELLED = "cancelled"

class InvoiceStatus(str, Enum):
    """
    Enumeration of invoice status values.
    
    Attributes:
        PENDING: Invoice is pending approval
        APPROVED: Invoice has been approved for payment
        REJECTED: Invoice has been rejected
        PAID: Invoice has been paid
        OVERDUE: Invoice is past due date
    """
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"
    OVERDUE = "overdue"

# Utility functions for datetime handling
def utc_now() -> datetime:
    """
    Return current UTC datetime using timezone-aware objects.
    
    This function ensures consistent timezone handling across the application
    by always returning UTC timestamps with proper timezone information.
    
    Returns:
        datetime: Current UTC datetime with timezone information
    """
    return datetime.now(timezone.utc)

# Base entity class for common fields
class BaseEntity(BaseModel):
    """
    Base class for all entities with common audit fields.
    
    This class provides standard fields that are common across all business
    entities, including unique identifiers and audit timestamps.
    
    Attributes:
        id: Unique identifier for the entity
        created_at: Timestamp when the entity was created
        updated_at: Timestamp when the entity was last updated
    """
    id: Optional[str] = Field(None, description="Unique identifier for the entity")
    created_at: Optional[datetime] = Field(None, description="Entity creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

# Vendor-related models
class VendorBase(BaseModel):
    """
    Base vendor model with core vendor information.
    
    This model contains all the essential information needed to manage
    vendor relationships, including contact details and payment terms.
    """
    name: str = Field(..., min_length=1, max_length=255, description="Vendor company name")
    email: EmailStr = Field(..., description="Primary contact email address")
    phone: Optional[str] = Field(None, description="Primary contact phone number")
    address: Optional[str] = Field(None, description="Vendor business address")
    tax_id: Optional[str] = Field(None, description="Tax identification number")
    payment_terms: Optional[str] = Field("Net 30", description="Payment terms (e.g., Net 30)")
    status: VendorStatus = Field(VendorStatus.ACTIVE, description="Current vendor status")

class VendorCreate(VendorBase):
    """
    Model for creating new vendors.
    
    This model is used for API endpoints that create new vendor records.
    It inherits all fields from VendorBase without modifications.
    """
    pass

class VendorUpdate(BaseModel):
    """
    Model for updating existing vendors.
    
    This model allows partial updates to vendor records by making all
    fields optional. Only provided fields will be updated.
    """
    name: Optional[str] = Field(None, description="Updated vendor company name")
    email: Optional[EmailStr] = Field(None, description="Updated email address")
    phone: Optional[str] = Field(None, description="Updated phone number")
    address: Optional[str] = Field(None, description="Updated business address")
    tax_id: Optional[str] = Field(None, description="Updated tax ID")
    payment_terms: Optional[str] = Field(None, description="Updated payment terms")
    status: Optional[VendorStatus] = Field(None, description="Updated vendor status")

class Vendor(VendorBase, BaseEntity):
    """
    Complete vendor model with audit fields.
    
    This model represents a fully-formed vendor entity including all
    business data and audit information from BaseEntity.
    """
    pass

# Purchase Order models
class PurchaseOrderBase(BaseModel):
    """
    Base purchase order model with essential procurement information.
    
    This model captures the core data needed for purchase order management,
    including vendor reference, line items, and approval status.
    """
    vendor_id: str = Field(..., description="Reference to the vendor")
    items: List[Dict[str, Union[str, float, int]]] = Field(..., description="List of ordered items")
    total_amount: float = Field(..., gt=0, description="Total order amount")
    status: Literal["pending", "approved", "rejected"] = Field("pending", description="Order status")

class PurchaseOrderCreate(PurchaseOrderBase):
    """
    Model for creating new purchase orders.
    
    Used by API endpoints for purchase order creation requests.
    """
    pass

class PurchaseOrderUpdate(BaseModel):
    """
    Model for updating existing purchase orders.
    
    Allows partial updates to purchase order records with all optional fields.
    """
    vendor_id: Optional[str] = Field(None, description="Updated vendor reference")
    items: Optional[List[Dict[str, Union[str, float, int]]]] = Field(None, description="Updated items list")
    total_amount: Optional[float] = Field(None, description="Updated total amount")
    status: Optional[Literal["pending", "approved", "rejected"]] = Field(None, description="Updated status")

class PurchaseOrder(PurchaseOrderBase, BaseEntity):
    """
    Complete purchase order model with audit information.
    
    Represents a full purchase order entity with business data and timestamps.
    """
    pass

# Invoice models
class InvoiceLineItem(BaseModel):
    """
    Model representing individual line items within an invoice.
    
    Each line item corresponds to a specific product or service being billed,
    with quantity, pricing, and reference information.
    """
    line_number: int = Field(..., description="Sequential line item number")
    po_line_reference: Optional[int] = Field(None, description="Reference to purchase order line")
    description: str = Field(..., description="Item description")
    quantity: int = Field(..., gt=0, description="Quantity ordered")
    unit_price: Decimal = Field(..., gt=0, description="Price per unit")
    total_amount: Decimal = Field(..., description="Total line amount")

class InvoiceBase(BaseModel):
    """
    Base invoice model with comprehensive billing information.
    
    This model captures all essential data for invoice processing, including
    vendor information, line items, financial details, and approval workflow.
    """
    vendor_id: str = Field(..., description="Reference to the billing vendor")
    po_id: Optional[str] = Field(None, description="Associated purchase order ID")
    invoice_number: str = Field(..., min_length=1, description="Vendor invoice number")
    invoice_date: datetime = Field(..., description="Date of invoice issuance")
    due_date: datetime = Field(..., description="Payment due date")
    line_items: List[InvoiceLineItem] = Field(..., description="List of invoice line items")
    subtotal: Decimal = Field(..., gt=0, description="Subtotal before tax")
    tax_amount: Decimal = Field(..., ge=0, description="Tax amount")
    total_amount: Decimal = Field(..., gt=0, description="Total amount due")
    status: InvoiceStatus = Field(InvoiceStatus.PENDING, description="Current invoice status")
    approved_by: Optional[str] = Field(None, description="User who approved the invoice")
    notes: Optional[str] = Field(None, description="Additional notes or comments")

class InvoiceCreate(InvoiceBase):
    """
    Model for creating new invoices.
    
    Used by API endpoints for invoice creation with full validation.
    """
    pass

class InvoiceUpdate(BaseModel):
    """
    Model for updating existing invoices.
    
    Supports partial updates to invoice records with optional fields.
    """
    invoice_date: Optional[datetime] = Field(None, description="Updated invoice date")
    due_date: Optional[datetime] = Field(None, description="Updated due date")
    line_items: Optional[List[InvoiceLineItem]] = Field(None, description="Updated line items")
    subtotal: Optional[Decimal] = Field(None, description="Updated subtotal")
    tax_amount: Optional[Decimal] = Field(None, description="Updated tax amount")
    total_amount: Optional[Decimal] = Field(None, description="Updated total amount")
    status: Optional[InvoiceStatus] = Field(None, description="Updated status")
    approved_by: Optional[str] = Field(None, description="Updated approver")
    notes: Optional[str] = Field(None, description="Updated notes")

class Invoice(InvoiceBase, BaseEntity):
    """
    Complete invoice model with audit fields.
    
    Represents a full invoice entity including all business data and audit trails.
    """
    pass

# Payment models
class PaymentBase(BaseModel):
    """
    Base payment model for financial transaction records.
    
    This model captures essential payment information including amounts,
    currency, approval status, and file references for payment processing.
    """
    invoice_id: str = Field(..., description="Reference to the paid invoice")
    vendor_id: str = Field(..., description="Reference to the payee vendor")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field("USD", description="Payment currency code")
    status: Literal["approved", "sent", "failed"] = Field("approved", description="Payment processing status")
    approved_at: datetime = Field(default_factory=utc_now, description="Payment approval timestamp")
    xml_s3_key: Optional[str] = Field(None, description="S3 key for XML payment file")
    json_s3_key: Optional[str] = Field(None, description="S3 key for JSON payment file")

class PaymentCreate(BaseModel):
    """
    Model for creating new payment records.
    
    Simplified model for payment creation with essential fields only.
    """
    invoice_id: str = Field(..., description="Invoice to be paid")
    vendor_id: str = Field(..., description="Vendor to be paid")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field("USD", description="Payment currency")

class PaymentUpdate(BaseModel):
    """
    Model for updating existing payment records.
    
    Supports updates to payment status, file references, and Workday integration fields.
    """
    amount: Optional[float] = Field(None, gt=0, description="Updated payment amount")
    currency: Optional[str] = Field(None, description="Updated currency")
    status: Optional[Literal["approved", "sent", "failed"]] = Field(None, description="Updated status")
    xml_s3_key: Optional[str] = Field(None, description="Updated XML file reference")
    json_s3_key: Optional[str] = Field(None, description="Updated JSON file reference")
    workday_confirmed_at: Optional[str] = Field(None, description="Workday confirmation timestamp")
    workday_callback_received: Optional[bool] = Field(None, description="Workday callback status")

class Payment(PaymentBase, BaseEntity):
    """
    Complete payment model with audit information.
    
    Represents a full payment entity with transaction data and audit trails.
    """
    pass

# API response models
class APIResponse(BaseModel):
    """
    Standardized API response wrapper for consistent response formatting.
    
    This model ensures all API responses follow a consistent structure
    with success indicators, messages, data payloads, and error information.
    """
    success: bool = Field(..., description="Indicates if the operation was successful")
    message: str = Field(..., description="Human-readable response message")
    data: Optional[Any] = Field(None, description="Response payload data")
    errors: Optional[List[str]] = Field(None, description="List of error messages if applicable")

class PaginatedResponse(BaseModel):
    """
    Standardized pagination response for list endpoints.
    
    This model provides consistent pagination metadata for API responses
    that return lists of items with page-based navigation.
    """
    items: List[Any] = Field(..., description="List of items for the current page")
    total: int = Field(..., description="Total number of items across all pages")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages") 