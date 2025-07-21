from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..models import Vendor, VendorCreate, VendorUpdate, APIResponse, PaginatedResponse
import uuid
from datetime import datetime

router = APIRouter()

# In-memory storage for development (will be replaced with DynamoDB)
vendors_db = {}

@router.get("/", response_model=PaginatedResponse)
async def list_vendors(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """List all vendors with pagination and optional status filter"""
    vendors_list = list(vendors_db.values())
    
    # Filter by status if provided
    if status:
        vendors_list = [v for v in vendors_list if v.status == status]
    
    # Pagination
    total = len(vendors_list)
    start = (page - 1) * size
    end = start + size
    items = vendors_list[start:end]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )

@router.post("/", response_model=APIResponse)
async def create_vendor(vendor: VendorCreate):
    """Create a new vendor"""
    vendor_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    new_vendor = Vendor(
        id=vendor_id,
        created_at=now,
        updated_at=now,
        **vendor.dict()
    )
    
    vendors_db[vendor_id] = new_vendor
    
    return APIResponse(
        success=True,
        message="Vendor created successfully",
        data=new_vendor
    )

@router.get("/{vendor_id}", response_model=APIResponse)
async def get_vendor(vendor_id: str):
    """Get a vendor by ID"""
    if vendor_id not in vendors_db:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    return APIResponse(
        success=True,
        message="Vendor retrieved successfully",
        data=vendors_db[vendor_id]
    )

@router.put("/{vendor_id}", response_model=APIResponse)
async def update_vendor(vendor_id: str, vendor_update: VendorUpdate):
    """Update a vendor"""
    if vendor_id not in vendors_db:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    existing_vendor = vendors_db[vendor_id]
    update_data = vendor_update.dict(exclude_unset=True)
    
    # Update fields
    for field, value in update_data.items():
        setattr(existing_vendor, field, value)
    
    existing_vendor.updated_at = datetime.utcnow()
    vendors_db[vendor_id] = existing_vendor
    
    return APIResponse(
        success=True,
        message="Vendor updated successfully",
        data=existing_vendor
    )

@router.delete("/{vendor_id}", response_model=APIResponse)
async def delete_vendor(vendor_id: str):
    """Delete a vendor"""
    if vendor_id not in vendors_db:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    deleted_vendor = vendors_db.pop(vendor_id)
    
    return APIResponse(
        success=True,
        message="Vendor deleted successfully",
        data={"id": vendor_id, "name": deleted_vendor.name}
    )

@router.get("/{vendor_id}/purchase-orders", response_model=APIResponse)
async def get_vendor_purchase_orders(vendor_id: str):
    """Get all purchase orders for a specific vendor"""
    if vendor_id not in vendors_db:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # This will be implemented when we have purchase orders
    return APIResponse(
        success=True,
        message="Vendor purchase orders retrieved successfully",
        data=[]
    ) 