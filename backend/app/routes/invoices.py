from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from ..models import APIResponse, PaginatedResponse
from ..services.dynamodb_service import db_service
import uuid

router = APIRouter()

# Simplified Invoice model as specified in requirements
class Invoice(BaseModel):
    id: str
    po_id: str
    invoice_number: str
    items: List[Dict[str, Union[str, float, int]]]
    total_amount: float
    status: Literal["received", "matched", "rejected"] = "received"
    submitted_at: datetime = Field(default_factory=datetime.utcnow)

class InvoiceCreate(BaseModel):
    po_id: str
    invoice_number: str
    items: List[Dict[str, Union[str, float, int]]]
    total_amount: float

class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    items: Optional[List[Dict[str, Union[str, float, int]]]] = None
    total_amount: Optional[float] = None
    status: Optional[Literal["received", "matched", "rejected"]] = None

@router.post("/", response_model=APIResponse)
async def create_invoice(invoice: InvoiceCreate):
    """Submit an invoice tied to a PO"""
    try:
        # Validate that the PO exists
        po_exists = await db_service.get_purchase_order(invoice.po_id)
        if not po_exists:
            raise HTTPException(status_code=400, detail=f"Purchase order with ID {invoice.po_id} not found")
        
        # Check if invoice number already exists
        existing_invoice = await db_service.get_invoice_by_number(invoice.invoice_number)
        if existing_invoice:
            raise HTTPException(status_code=400, detail=f"Invoice number {invoice.invoice_number} already exists")
        
        # Create invoice in DynamoDB
        invoice_data = invoice.dict()
        invoice_data['status'] = 'received'  # Default status
        
        created_invoice_data = await db_service.create_invoice(invoice_data)
        
        # Convert to Invoice object
        new_invoice = Invoice(**created_invoice_data)
        
        return APIResponse(
            success=True,
            message="Invoice created successfully",
            data=new_invoice
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{invoice_id}", response_model=APIResponse)
async def get_invoice(invoice_id: str):
    """Fetch a single invoice"""
    try:
        # Get invoice from DynamoDB
        invoice_data = await db_service.get_invoice(invoice_id)
        
        if not invoice_data:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Convert to Invoice object
        invoice = Invoice(**invoice_data)
        
        return APIResponse(
            success=True,
            message="Invoice retrieved successfully",
            data=invoice
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=PaginatedResponse)
async def list_invoices(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    po_id: Optional[str] = Query(None, description="Filter by PO ID"),
    status: Optional[Literal["received", "matched", "rejected"]] = Query(None, description="Filter by status")
):
    """List all invoices with optional PO filter"""
    try:
        # Get invoices from DynamoDB with filters
        invoices_data = await db_service.list_invoices(
            po_id_filter=po_id,
            status_filter=status
        )
        
        # Convert to Invoice objects
        invoices_list = [Invoice(**invoice_data) for invoice_data in invoices_data]
        
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{invoice_id}/reconcile", response_model=APIResponse)
async def reconcile_invoice(invoice_id: str):
    """Trigger reconciliation check (validate against PO)"""
    try:
        # Get invoice from DynamoDB
        invoice_data = await db_service.get_invoice(invoice_id)
        
        if not invoice_data:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get associated purchase order
        po_data = await db_service.get_purchase_order(invoice_data['po_id'])
        
        if not po_data:
            raise HTTPException(status_code=400, detail="Associated purchase order not found")
        
        # Perform reconciliation logic
        reconciliation_result = await db_service.reconcile_invoice_with_po(invoice_id, invoice_data, po_data)
        
        # Update invoice status based on reconciliation
        updated_invoice_data = await db_service.update_invoice(invoice_id, {
            'status': reconciliation_result['status']
        })
        
        # Convert to Invoice object
        updated_invoice = Invoice(**updated_invoice_data)
        
        return APIResponse(
            success=True,
            message=f"Invoice reconciliation completed: {reconciliation_result['message']}",
            data={
                "invoice": updated_invoice,
                "reconciliation_details": reconciliation_result['details']
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{invoice_id}", response_model=APIResponse)
async def update_invoice(invoice_id: str, invoice_update: InvoiceUpdate):
    """Update an invoice"""
    try:
        # Get update data, excluding unset fields
        update_data = invoice_update.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Update invoice in DynamoDB
        updated_invoice_data = await db_service.update_invoice(invoice_id, update_data)
        
        # Convert to Invoice object
        updated_invoice = Invoice(**updated_invoice_data)
        
        return APIResponse(
            success=True,
            message="Invoice updated successfully",
            data=updated_invoice
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Invoice not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{invoice_id}", response_model=APIResponse)
async def delete_invoice(invoice_id: str):
    """Delete invoice (with audit logging)"""
    try:
        # Get invoice details before deleting
        invoice_data = await db_service.get_invoice(invoice_id)
        
        if not invoice_data:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Delete invoice from DynamoDB
        await db_service.delete_invoice(invoice_id)
        
        return APIResponse(
            success=True,
            message="Invoice deleted successfully",
            data={
                "id": invoice_id, 
                "invoice_number": invoice_data.get("invoice_number", "Unknown")
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Invoice not found")
        raise HTTPException(status_code=500, detail=str(e)) 