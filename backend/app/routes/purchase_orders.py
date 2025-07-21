from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..models import PurchaseOrder, PurchaseOrderCreate, PurchaseOrderUpdate, APIResponse, PaginatedResponse, POStatus
from ..services.dynamodb_service import db_service
import uuid
from datetime import datetime

router = APIRouter()

@router.get("/", response_model=PaginatedResponse)
async def list_purchase_orders(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    status: Optional[POStatus] = Query(None, description="Filter by status"),
    vendor_id: Optional[str] = Query(None, description="Filter by vendor ID")
):
    """List all purchase orders with pagination and optional filters"""
    try:
        # Get purchase orders from DynamoDB
        status_filter = status.value if status else None
        pos_data = await db_service.list_purchase_orders(
            status_filter=status_filter,
            vendor_id_filter=vendor_id
        )
        
        # Convert to PurchaseOrder objects
        pos_list = [PurchaseOrder(**po_data) for po_data in pos_data]
        
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=APIResponse)
async def create_purchase_order(po: PurchaseOrderCreate):
    """Create a new purchase order"""
    try:
        # Create purchase order in DynamoDB
        po_data = await db_service.create_purchase_order(po.dict())
        
        # Convert to PurchaseOrder object
        new_po = PurchaseOrder(**po_data)
        
        return APIResponse(
            success=True,
            message="Purchase order created successfully",
            data=new_po
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{po_id}", response_model=APIResponse)
async def get_purchase_order(po_id: str):
    """Get a purchase order by ID"""
    try:
        # Get purchase order from DynamoDB
        po_data = await db_service.get_purchase_order(po_id)
        
        if not po_data:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        
        # Convert to PurchaseOrder object
        po = PurchaseOrder(**po_data)
        
        return APIResponse(
            success=True,
            message="Purchase order retrieved successfully",
            data=po
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{po_id}", response_model=APIResponse)
async def update_purchase_order(po_id: str, po_update: PurchaseOrderUpdate):
    """Update a purchase order"""
    try:
        # Get update data, excluding unset fields
        update_data = po_update.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Update purchase order in DynamoDB
        updated_po_data = await db_service.update_purchase_order(po_id, update_data)
        
        # Convert to PurchaseOrder object
        updated_po = PurchaseOrder(**updated_po_data)
        
        return APIResponse(
            success=True,
            message="Purchase order updated successfully",
            data=updated_po
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Purchase order not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{po_id}", response_model=APIResponse)
async def delete_purchase_order(po_id: str):
    """Delete a purchase order"""
    try:
        # Get purchase order details before deleting
        po_data = await db_service.get_purchase_order(po_id)
        
        if not po_data:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        
        # Delete purchase order from DynamoDB
        await db_service.delete_purchase_order(po_id)
        
        return APIResponse(
            success=True,
            message="Purchase order deleted successfully",
            data={"id": po_id, "po_number": po_data.get("po_number", "Unknown")}
        )
    except HTTPException:
        raise
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Purchase order not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{po_id}/approve", response_model=APIResponse)
async def approve_purchase_order(po_id: str, approved_by: str):
    """Approve a purchase order"""
    try:
        # Get current purchase order
        po_data = await db_service.get_purchase_order(po_id)
        
        if not po_data:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        
        # Check current status
        current_status = po_data.get("status")
        if current_status != POStatus.DRAFT.value:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot approve purchase order with status: {current_status}"
            )
        
        # Update purchase order with approval
        update_data = {
            "status": POStatus.APPROVED.value,
            "approved_by": approved_by
        }
        
        updated_po_data = await db_service.update_purchase_order(po_id, update_data)
        updated_po = PurchaseOrder(**updated_po_data)
        
        return APIResponse(
            success=True,
            message="Purchase order approved successfully",
            data=updated_po
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{po_id}/send", response_model=APIResponse)
async def send_purchase_order(po_id: str):
    """Send a purchase order to vendor"""
    try:
        # Get current purchase order
        po_data = await db_service.get_purchase_order(po_id)
        
        if not po_data:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        
        # Check current status
        current_status = po_data.get("status")
        if current_status != POStatus.APPROVED.value:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot send purchase order with status: {current_status}"
            )
        
        # Update purchase order status to sent
        update_data = {
            "status": POStatus.SENT.value
        }
        
        updated_po_data = await db_service.update_purchase_order(po_id, update_data)
        updated_po = PurchaseOrder(**updated_po_data)
        
        return APIResponse(
            success=True,
            message="Purchase order sent to vendor successfully",
            data=updated_po
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 