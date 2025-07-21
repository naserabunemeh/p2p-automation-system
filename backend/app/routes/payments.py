from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from typing import List, Optional
from ..models import Payment, PaymentCreate, PaymentUpdate, APIResponse, PaginatedResponse, PaymentStatus
import uuid
import json
from datetime import datetime

router = APIRouter()

# In-memory storage for development (will be replaced with DynamoDB)
payments_db = {}

@router.get("/", response_model=PaginatedResponse)
async def list_payments(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    status: Optional[PaymentStatus] = Query(None, description="Filter by status"),
    vendor_id: Optional[str] = Query(None, description="Filter by vendor ID"),
    invoice_id: Optional[str] = Query(None, description="Filter by invoice ID")
):
    """List all payments with pagination and optional filters"""
    payments_list = list(payments_db.values())
    
    # Filter by status if provided
    if status:
        payments_list = [p for p in payments_list if p.status == status]
    
    # Filter by vendor_id if provided
    if vendor_id:
        payments_list = [p for p in payments_list if p.vendor_id == vendor_id]
    
    # Filter by invoice_id if provided
    if invoice_id:
        payments_list = [p for p in payments_list if p.invoice_id == invoice_id]
    
    # Pagination
    total = len(payments_list)
    start = (page - 1) * size
    end = start + size
    items = payments_list[start:end]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )

@router.post("/", response_model=APIResponse)
async def create_payment(payment: PaymentCreate):
    """Create a new payment"""
    payment_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    new_payment = Payment(
        id=payment_id,
        created_at=now,
        updated_at=now,
        **payment.dict()
    )
    
    payments_db[payment_id] = new_payment
    
    return APIResponse(
        success=True,
        message="Payment created successfully",
        data=new_payment
    )

@router.get("/{payment_id}", response_model=APIResponse)
async def get_payment(payment_id: str):
    """Get a payment by ID"""
    if payment_id not in payments_db:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return APIResponse(
        success=True,
        message="Payment retrieved successfully",
        data=payments_db[payment_id]
    )

@router.put("/{payment_id}", response_model=APIResponse)
async def update_payment(payment_id: str, payment_update: PaymentUpdate):
    """Update a payment"""
    if payment_id not in payments_db:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    existing_payment = payments_db[payment_id]
    update_data = payment_update.dict(exclude_unset=True)
    
    # Update fields
    for field, value in update_data.items():
        setattr(existing_payment, field, value)
    
    existing_payment.updated_at = datetime.utcnow()
    payments_db[payment_id] = existing_payment
    
    return APIResponse(
        success=True,
        message="Payment updated successfully",
        data=existing_payment
    )

@router.delete("/{payment_id}", response_model=APIResponse)
async def delete_payment(payment_id: str):
    """Delete a payment"""
    if payment_id not in payments_db:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    deleted_payment = payments_db.pop(payment_id)
    
    return APIResponse(
        success=True,
        message="Payment deleted successfully",
        data={"id": payment_id, "reference_number": deleted_payment.reference_number}
    )

@router.post("/{payment_id}/process", response_model=APIResponse)
async def process_payment(payment_id: str, processed_by: str):
    """Process a payment"""
    if payment_id not in payments_db:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = payments_db[payment_id]
    
    if payment.status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot process payment with status: {payment.status}"
        )
    
    payment.status = PaymentStatus.PROCESSING
    payment.processed_by = processed_by
    payment.payment_date = datetime.utcnow()
    payment.reference_number = f"PAY-{payment_id[:8].upper()}"
    payment.updated_at = datetime.utcnow()
    
    payments_db[payment_id] = payment
    
    return APIResponse(
        success=True,
        message="Payment processing initiated successfully",
        data=payment
    )

@router.post("/{payment_id}/complete", response_model=APIResponse)
async def complete_payment(payment_id: str):
    """Mark a payment as completed"""
    if payment_id not in payments_db:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = payments_db[payment_id]
    
    if payment.status != PaymentStatus.PROCESSING:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot complete payment with status: {payment.status}"
        )
    
    payment.status = PaymentStatus.COMPLETED
    payment.updated_at = datetime.utcnow()
    
    payments_db[payment_id] = payment
    
    return APIResponse(
        success=True,
        message="Payment completed successfully",
        data=payment
    )

@router.get("/{payment_id}/xml")
async def get_payment_xml(payment_id: str):
    """Generate XML payment file"""
    if payment_id not in payments_db:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = payments_db[payment_id]
    
    # Generate XML content (basic structure)
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<payment xmlns="http://www.w3.org/2001/XMLSchema-instance">
    <payment_id>{payment.id}</payment_id>
    <invoice_id>{payment.invoice_id}</invoice_id>
    <vendor_id>{payment.vendor_id}</vendor_id>
    <payment_amount>{payment.payment_amount}</payment_amount>
    <payment_method>{payment.payment_method}</payment_method>
    <payment_date>{payment.payment_date.isoformat() if payment.payment_date else ''}</payment_date>
    <reference_number>{payment.reference_number or ''}</reference_number>
    <status>{payment.status}</status>
    <processed_by>{payment.processed_by or ''}</processed_by>
    <created_at>{payment.created_at.isoformat() if payment.created_at else ''}</created_at>
    <updated_at>{payment.updated_at.isoformat() if payment.updated_at else ''}</updated_at>
    <notes>{payment.notes or ''}</notes>
</payment>"""
    
    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=payment_{payment_id}.xml"}
    )

@router.get("/{payment_id}/json")
async def get_payment_json(payment_id: str):
    """Generate JSON payment file"""
    if payment_id not in payments_db:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = payments_db[payment_id]
    
    # Convert payment to dict and handle datetime serialization
    payment_dict = payment.dict()
    for key, value in payment_dict.items():
        if isinstance(value, datetime):
            payment_dict[key] = value.isoformat()
    
    json_content = json.dumps(payment_dict, indent=2, default=str)
    
    return Response(
        content=json_content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=payment_{payment_id}.json"}
    ) 