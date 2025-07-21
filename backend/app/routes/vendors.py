from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..models import Vendor, VendorCreate, VendorUpdate, APIResponse, PaginatedResponse
from ..services.dynamodb_service import db_service
import uuid
from datetime import datetime

router = APIRouter()

@router.get("/", response_model=PaginatedResponse)
async def list_vendors(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """List all vendors with pagination and optional status filter"""
    try:
        # Get vendors from DynamoDB
        vendors_data = await db_service.list_vendors(status_filter=status)
        
        # Convert to Vendor objects
        vendors_list = [Vendor(**vendor_data) for vendor_data in vendors_data]
        
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=APIResponse)
async def create_vendor(vendor: VendorCreate):
    """Create a new vendor"""
    try:
        # Create vendor in DynamoDB - use model_dump with by_alias=True to properly serialize enums
        vendor_dict = vendor.model_dump(mode='json')  # This properly serializes enums to their values
        
        vendor_data = await db_service.create_vendor(vendor_dict)
        
        # Convert to Vendor object
        new_vendor = Vendor(**vendor_data)
        
        return APIResponse(
            success=True,
            message="Vendor created successfully",
            data=new_vendor
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{vendor_id}", response_model=APIResponse)
async def get_vendor(vendor_id: str):
    """Get a vendor by ID"""
    try:
        # Get vendor from DynamoDB
        vendor_data = await db_service.get_vendor(vendor_id)
        
        if not vendor_data:
            raise HTTPException(status_code=404, detail="Vendor not found")
        
        # Convert to Vendor object
        vendor = Vendor(**vendor_data)
        
        return APIResponse(
            success=True,
            message="Vendor retrieved successfully",
            data=vendor
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{vendor_id}", response_model=APIResponse)
async def update_vendor(vendor_id: str, vendor_update: VendorUpdate):
    """Update a vendor"""
    try:
        # Get update data, excluding unset fields
        update_data = vendor_update.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Update vendor in DynamoDB
        updated_vendor_data = await db_service.update_vendor(vendor_id, update_data)
        
        # Convert to Vendor object
        updated_vendor = Vendor(**updated_vendor_data)
        
        return APIResponse(
            success=True,
            message="Vendor updated successfully",
            data=updated_vendor
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Vendor not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{vendor_id}", response_model=APIResponse)
async def delete_vendor(vendor_id: str):
    """Delete a vendor"""
    try:
        # Get vendor details before deleting
        vendor_data = await db_service.get_vendor(vendor_id)
        
        if not vendor_data:
            raise HTTPException(status_code=404, detail="Vendor not found")
        
        # Delete vendor from DynamoDB
        await db_service.delete_vendor(vendor_id)
        
        return APIResponse(
            success=True,
            message="Vendor deleted successfully",
            data={"id": vendor_id, "name": vendor_data.get("name", "Unknown")}
        )
    except HTTPException:
        raise
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Vendor not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{vendor_id}/purchase-orders", response_model=APIResponse)
async def get_vendor_purchase_orders(vendor_id: str):
    """Get all purchase orders for a specific vendor"""
    try:
        # Check if vendor exists
        vendor_data = await db_service.get_vendor(vendor_id)
        if not vendor_data:
            raise HTTPException(status_code=404, detail="Vendor not found")
        
        # Get purchase orders for this vendor
        po_list = await db_service.list_purchase_orders(vendor_id_filter=vendor_id)
        
        return APIResponse(
            success=True,
            message="Vendor purchase orders retrieved successfully",
            data=po_list
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 