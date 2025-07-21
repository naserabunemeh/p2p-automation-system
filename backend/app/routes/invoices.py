from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..models import Invoice, InvoiceCreate, InvoiceUpdate, APIResponse, PaginatedResponse, InvoiceStatus
import uuid
from datetime import datetime

router = APIRouter()

# In-memory storage for development (will be replaced with DynamoDB)
invoices_db = {}

@router.get("/", response_model=PaginatedResponse)
async def list_invoices(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    status: Optional[InvoiceStatus] = Query(None, description="Filter by status"),
    vendor_id: Optional[str] = Query(None, description="Filter by vendor ID"),
    po_id: Optional[str] = Query(None, description="Filter by purchase order ID")
):
    """List all invoices with pagination and optional filters"""
    invoices_list = list(invoices_db.values())
    
    # Filter by status if provided
    if status:
        invoices_list = [inv for inv in invoices_list if inv.status == status]
    
    # Filter by vendor_id if provided
    if vendor_id:
        invoices_list = [inv for inv in invoices_list if inv.vendor_id == vendor_id]
    
    # Filter by po_id if provided
    if po_id:
        invoices_list = [inv for inv in invoices_list if inv.po_id == po_id]
    
    # Pagination
    total = len(invoices_list)
    start = (page - 1) * size
    end = start + size
    items = invoices_list[start:end]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )

@router.post("/", response_model=APIResponse)
async def create_invoice(invoice: InvoiceCreate):
    """Create a new invoice"""
    invoice_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    new_invoice = Invoice(
        id=invoice_id,
        created_at=now,
        updated_at=now,
        **invoice.dict()
    )
    
    invoices_db[invoice_id] = new_invoice
    
    return APIResponse(
        success=True,
        message="Invoice created successfully",
        data=new_invoice
    )

@router.get("/{invoice_id}", response_model=APIResponse)
async def get_invoice(invoice_id: str):
    """Get an invoice by ID"""
    if invoice_id not in invoices_db:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return APIResponse(
        success=True,
        message="Invoice retrieved successfully",
        data=invoices_db[invoice_id]
    )

@router.put("/{invoice_id}", response_model=APIResponse)
async def update_invoice(invoice_id: str, invoice_update: InvoiceUpdate):
    """Update an invoice"""
    if invoice_id not in invoices_db:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    existing_invoice = invoices_db[invoice_id]
    update_data = invoice_update.dict(exclude_unset=True)
    
    # Update fields
    for field, value in update_data.items():
        setattr(existing_invoice, field, value)
    
    existing_invoice.updated_at = datetime.utcnow()
    invoices_db[invoice_id] = existing_invoice
    
    return APIResponse(
        success=True,
        message="Invoice updated successfully",
        data=existing_invoice
    )

@router.delete("/{invoice_id}", response_model=APIResponse)
async def delete_invoice(invoice_id: str):
    """Delete an invoice"""
    if invoice_id not in invoices_db:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    deleted_invoice = invoices_db.pop(invoice_id)
    
    return APIResponse(
        success=True,
        message="Invoice deleted successfully",
        data={"id": invoice_id, "invoice_number": deleted_invoice.invoice_number}
    )

@router.post("/{invoice_id}/approve", response_model=APIResponse)
async def approve_invoice(invoice_id: str, approved_by: str, notes: Optional[str] = None):
    """Approve an invoice"""
    if invoice_id not in invoices_db:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice = invoices_db[invoice_id]
    
    if invoice.status != InvoiceStatus.PENDING:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot approve invoice with status: {invoice.status}"
        )
    
    invoice.status = InvoiceStatus.APPROVED
    invoice.approved_by = approved_by
    if notes:
        invoice.notes = notes
    invoice.updated_at = datetime.utcnow()
    
    invoices_db[invoice_id] = invoice
    
    return APIResponse(
        success=True,
        message="Invoice approved successfully",
        data=invoice
    )

@router.post("/{invoice_id}/reject", response_model=APIResponse)
async def reject_invoice(invoice_id: str, rejected_by: str, rejection_reason: str):
    """Reject an invoice"""
    if invoice_id not in invoices_db:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice = invoices_db[invoice_id]
    
    if invoice.status not in [InvoiceStatus.PENDING, InvoiceStatus.APPROVED]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot reject invoice with status: {invoice.status}"
        )
    
    invoice.status = InvoiceStatus.REJECTED
    invoice.approved_by = rejected_by
    invoice.notes = f"Rejected: {rejection_reason}"
    invoice.updated_at = datetime.utcnow()
    
    invoices_db[invoice_id] = invoice
    
    return APIResponse(
        success=True,
        message="Invoice rejected successfully",
        data=invoice
    )

@router.get("/{invoice_id}/payment-ready", response_model=APIResponse)
async def check_payment_ready(invoice_id: str):
    """Check if an invoice is ready for payment"""
    if invoice_id not in invoices_db:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice = invoices_db[invoice_id]
    
    is_ready = invoice.status == InvoiceStatus.APPROVED
    
    return APIResponse(
        success=True,
        message="Payment readiness checked successfully",
        data={
            "invoice_id": invoice_id,
            "is_payment_ready": is_ready,
            "status": invoice.status,
            "due_date": invoice.due_date,
            "total_amount": invoice.total_amount
        }
    ) 