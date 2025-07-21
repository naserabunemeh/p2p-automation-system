from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..models import PurchaseOrder, PurchaseOrderCreate, PurchaseOrderUpdate, APIResponse, PaginatedResponse, POStatus
import uuid
from datetime import datetime

router = APIRouter()

# In-memory storage for development (will be replaced with DynamoDB)
purchase_orders_db = {}

@router.get("/", response_model=PaginatedResponse)
async def list_purchase_orders(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    status: Optional[POStatus] = Query(None, description="Filter by status"),
    vendor_id: Optional[str] = Query(None, description="Filter by vendor ID")
):
    """List all purchase orders with pagination and optional filters"""
    pos_list = list(purchase_orders_db.values())
    
    # Filter by status if provided
    if status:
        pos_list = [po for po in pos_list if po.status == status]
    
    # Filter by vendor_id if provided
    if vendor_id:
        pos_list = [po for po in pos_list if po.vendor_id == vendor_id]
    
    # Pagination
    total = len(pos_list)
    start = (page - 1) * size
    end = start + size
    items = pos_list[start:end]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )

@router.post("/", response_model=APIResponse)
async def create_purchase_order(po: PurchaseOrderCreate):
    """Create a new purchase order"""
    po_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    new_po = PurchaseOrder(
        id=po_id,
        created_at=now,
        updated_at=now,
        **po.dict()
    )
    
    purchase_orders_db[po_id] = new_po
    
    return APIResponse(
        success=True,
        message="Purchase order created successfully",
        data=new_po
    )

@router.get("/{po_id}", response_model=APIResponse)
async def get_purchase_order(po_id: str):
    """Get a purchase order by ID"""
    if po_id not in purchase_orders_db:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    return APIResponse(
        success=True,
        message="Purchase order retrieved successfully",
        data=purchase_orders_db[po_id]
    )

@router.put("/{po_id}", response_model=APIResponse)
async def update_purchase_order(po_id: str, po_update: PurchaseOrderUpdate):
    """Update a purchase order"""
    if po_id not in purchase_orders_db:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    existing_po = purchase_orders_db[po_id]
    update_data = po_update.dict(exclude_unset=True)
    
    # Update fields
    for field, value in update_data.items():
        setattr(existing_po, field, value)
    
    existing_po.updated_at = datetime.utcnow()
    purchase_orders_db[po_id] = existing_po
    
    return APIResponse(
        success=True,
        message="Purchase order updated successfully",
        data=existing_po
    )

@router.delete("/{po_id}", response_model=APIResponse)
async def delete_purchase_order(po_id: str):
    """Delete a purchase order"""
    if po_id not in purchase_orders_db:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    deleted_po = purchase_orders_db.pop(po_id)
    
    return APIResponse(
        success=True,
        message="Purchase order deleted successfully",
        data={"id": po_id, "po_number": deleted_po.po_number}
    )

@router.post("/{po_id}/approve", response_model=APIResponse)
async def approve_purchase_order(po_id: str, approved_by: str):
    """Approve a purchase order"""
    if po_id not in purchase_orders_db:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    po = purchase_orders_db[po_id]
    
    if po.status != POStatus.DRAFT:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot approve purchase order with status: {po.status}"
        )
    
    po.status = POStatus.APPROVED
    po.approved_by = approved_by
    po.updated_at = datetime.utcnow()
    
    purchase_orders_db[po_id] = po
    
    return APIResponse(
        success=True,
        message="Purchase order approved successfully",
        data=po
    )

@router.post("/{po_id}/send", response_model=APIResponse)
async def send_purchase_order(po_id: str):
    """Send a purchase order to vendor"""
    if po_id not in purchase_orders_db:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    po = purchase_orders_db[po_id]
    
    if po.status != POStatus.APPROVED:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot send purchase order with status: {po.status}"
        )
    
    po.status = POStatus.SENT
    po.updated_at = datetime.utcnow()
    
    purchase_orders_db[po_id] = po
    
    return APIResponse(
        success=True,
        message="Purchase order sent to vendor successfully",
        data=po
    ) 