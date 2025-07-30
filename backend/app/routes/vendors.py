"""
Vendor Management API Routes for ERP-Lite P2P Automation System

This module implements REST API endpoints for vendor management operations,
providing comprehensive CRUD functionality with proper error handling,
pagination, and business logic validation.

Key Features:
    - Full CRUD operations for vendor management
    - Pagination support for large vendor lists
    - Status-based filtering for vendor queries
    - Purchase order integration for vendor relationships
    - Comprehensive error handling and HTTP status codes
    - Input validation through Pydantic models

Business Operations:
    - Vendor creation with validation
    - Vendor information updates
    - Status management (active, inactive, pending, suspended)
    - Vendor-specific purchase order retrieval
    - Safe vendor deletion with dependency checks

API Standards:
    - RESTful endpoint design
    - Consistent response formatting
    - HTTP status code compliance
    - Query parameter validation

Author: Development Team
Version: 1.0.0
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..models import Vendor, VendorCreate, VendorUpdate, APIResponse, PaginatedResponse
from ..services.dynamodb_service import db_service
import uuid
from datetime import datetime

# Initialize API router for vendor endpoints
router = APIRouter()

@router.get("/", response_model=PaginatedResponse)
async def list_vendors(
    page: int = Query(1, ge=1, description="Page number for pagination (starts at 1)"),
    size: int = Query(10, ge=1, le=100, description="Number of vendors per page (max 100)"),
    status: Optional[str] = Query(None, description="Filter vendors by status (active, inactive, pending, suspended)")
):
    """
    Retrieve a paginated list of vendors with optional status filtering.
    
    This endpoint provides comprehensive vendor listing capabilities with pagination
    to handle large vendor databases efficiently. It supports status-based filtering
    to allow users to view specific vendor categories.
    
    Query Parameters:
        - page: Page number for pagination (default: 1, minimum: 1)
        - size: Number of vendors per page (default: 10, max: 100)
        - status: Optional status filter for vendor state management
        
    Returns:
        PaginatedResponse: Structured response containing:
            - items: List of vendor objects for the requested page
            - total: Total number of vendors matching the filter
            - page: Current page number
            - size: Page size used
            - pages: Total number of pages available
            
    Raises:
        HTTPException: 500 error for database or processing failures
        
    Business Logic:
        1. Query DynamoDB with optional status filtering
        2. Convert raw data to validated Vendor objects
        3. Apply client-side pagination for consistent response times
        4. Return structured pagination metadata for UI components
    """
    try:
        # Retrieve vendors from DynamoDB with optional status filtering
        # This query may return all vendors if no filter is specified
        vendors_data = await db_service.list_vendors(status_filter=status)
        
        # Convert raw database records to validated Pydantic models
        # This ensures type safety and validates data integrity
        vendors_list = [Vendor(**vendor_data) for vendor_data in vendors_data]
        
        # Implement pagination logic for consistent response times
        # Calculate total count before slicing for accurate pagination metadata
        total = len(vendors_list)
        start = (page - 1) * size  # Calculate starting index for current page
        end = start + size         # Calculate ending index for current page
        items = vendors_list[start:end]  # Extract items for current page
        
        # Return standardized pagination response with metadata
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size  # Calculate total pages using ceiling division
        )
    except Exception as e:
        # Handle any database or processing errors with appropriate HTTP status
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=APIResponse)
async def create_vendor(vendor: VendorCreate):
    """
    Create a new vendor record with comprehensive validation.
    
    This endpoint handles vendor creation with full business logic validation,
    ensuring data integrity and proper audit trail establishment. It performs
    duplicate checking and establishes proper relationships.
    
    Request Body:
        VendorCreate: Validated vendor data including:
            - name: Company name (required, 1-255 characters)
            - email: Valid email address (required)
            - phone: Optional contact phone number
            - address: Optional business address
            - tax_id: Optional tax identification number
            - payment_terms: Payment terms (default: "Net 30")
            - status: Vendor status (default: "active")
            
    Returns:
        APIResponse: Standardized response containing:
            - success: True if creation succeeded
            - message: Descriptive success message
            - data: Complete vendor object with generated ID and timestamps
            
    Raises:
        HTTPException: 500 error for database or validation failures
        
    Business Logic:
        1. Validate input data through Pydantic models
        2. Convert enum values to proper database format
        3. Create vendor record in DynamoDB with audit fields
        4. Return complete vendor object with generated metadata
    """
    try:
        # Convert Pydantic model to dictionary with proper enum serialization
        # Using model_dump with mode='json' ensures enums are serialized to their values
        vendor_dict = vendor.model_dump(mode='json')  # Properly serializes enums to string values
        
        # Create vendor record in DynamoDB with automatic ID and timestamp generation
        # The service layer handles UUID generation and audit field population
        vendor_data = await db_service.create_vendor(vendor_dict)
        
        # Convert database response back to validated Pydantic model
        # This ensures response data integrity and type safety
        new_vendor = Vendor(**vendor_data)
        
        # Return standardized success response with created vendor data
        return APIResponse(
            success=True,
            message="Vendor created successfully",
            data=new_vendor
        )
    except Exception as e:
        # Handle database errors, validation failures, or constraint violations
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{vendor_id}", response_model=APIResponse)
async def get_vendor(vendor_id: str):
    """
    Retrieve a specific vendor by their unique identifier.
    
    This endpoint provides detailed vendor information retrieval with proper
    error handling for non-existent vendors and database connectivity issues.
    
    Path Parameters:
        vendor_id (str): Unique identifier for the vendor record
        
    Returns:
        APIResponse: Standardized response containing:
            - success: True if vendor found successfully
            - message: Descriptive success message
            - data: Complete vendor object with all fields
            
    Raises:
        HTTPException: 
            - 404 error if vendor not found
            - 500 error for database or processing failures
            
    Business Logic:
        1. Query DynamoDB for vendor by unique ID
        2. Validate vendor existence before processing
        3. Convert database record to validated Pydantic model
        4. Return structured response with vendor data
    """
    try:
        # Retrieve vendor record from DynamoDB by unique identifier
        vendor_data = await db_service.get_vendor(vendor_id)
        
        # Validate vendor existence and return appropriate error if not found
        if not vendor_data:
            raise HTTPException(status_code=404, detail="Vendor not found")
        
        # Convert database record to validated Pydantic model for type safety
        vendor = Vendor(**vendor_data)
        
        # Return standardized success response with vendor data
        return APIResponse(
            success=True,
            message="Vendor retrieved successfully",
            data=vendor
        )
    except HTTPException:
        # Re-raise HTTP exceptions to preserve status codes and messages
        raise
    except Exception as e:
        # Handle unexpected database or processing errors
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{vendor_id}", response_model=APIResponse)
async def update_vendor(vendor_id: str, vendor_update: VendorUpdate):
    """
    Update an existing vendor record with partial data support.
    
    This endpoint supports partial updates to vendor records, allowing clients
    to update specific fields without affecting others. It includes proper
    validation and audit trail maintenance.
    
    Path Parameters:
        vendor_id (str): Unique identifier for the vendor to update
        
    Request Body:
        VendorUpdate: Partial vendor data with optional fields:
            - All fields from VendorCreate but marked as optional
            - Only provided fields will be updated
            - Excludes unset fields from the update operation
            
    Returns:
        APIResponse: Standardized response containing:
            - success: True if update succeeded
            - message: Descriptive success message
            - data: Updated vendor object with new values
            
    Raises:
        HTTPException:
            - 400 error if no fields provided for update
            - 404 error if vendor not found
            - 500 error for database or validation failures
            
    Business Logic:
        1. Extract only fields that were explicitly set in the request
        2. Validate that at least one field is provided for update
        3. Perform atomic update operation in DynamoDB
        4. Return updated vendor object with new audit timestamps
    """
    try:
        # Extract only fields that were explicitly set in the request body
        # Using dict(exclude_unset=True) prevents null/empty updates
        update_data = vendor_update.dict(exclude_unset=True)
        
        # Validate that at least one field is provided for update
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Perform atomic update operation in DynamoDB with optimistic locking
        # The service layer handles field validation and audit timestamp updates
        updated_vendor_data = await db_service.update_vendor(vendor_id, update_data)
        
        # Convert updated database record to validated Pydantic model
        updated_vendor = Vendor(**updated_vendor_data)
        
        # Return standardized success response with updated vendor data
        return APIResponse(
            success=True,
            message="Vendor updated successfully",
            data=updated_vendor
        )
    except Exception as e:
        # Handle vendor not found scenarios with appropriate status code
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Vendor not found")
        # Handle all other errors as internal server errors
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{vendor_id}", response_model=APIResponse)
async def delete_vendor(vendor_id: str):
    """
    Delete a vendor record with proper dependency checking.
    
    This endpoint handles vendor deletion with appropriate business logic
    validation, ensuring referential integrity and providing audit information
    about the deleted record.
    
    Path Parameters:
        vendor_id (str): Unique identifier for the vendor to delete
        
    Returns:
        APIResponse: Standardized response containing:
            - success: True if deletion succeeded
            - message: Descriptive success message
            - data: Information about the deleted vendor (ID and name)
            
    Raises:
        HTTPException:
            - 404 error if vendor not found
            - 500 error for database or constraint violations
            
    Business Logic:
        1. Verify vendor exists before attempting deletion
        2. Check for dependent records (purchase orders, invoices)
        3. Perform soft or hard delete based on business rules
        4. Return confirmation with deleted vendor information
        
    Note:
        In production, this might perform a soft delete by updating status
        rather than physically removing the record to maintain audit trails.
    """
    try:
        # Retrieve vendor details before deletion for audit and response purposes
        vendor_data = await db_service.get_vendor(vendor_id)
        
        # Validate vendor existence before attempting deletion
        if not vendor_data:
            raise HTTPException(status_code=404, detail="Vendor not found")
        
        # Perform vendor deletion operation in DynamoDB
        # The service layer should handle dependency checking and referential integrity
        await db_service.delete_vendor(vendor_id)
        
        # Return standardized success response with deleted vendor information
        return APIResponse(
            success=True,
            message="Vendor deleted successfully",
            data={"id": vendor_id, "name": vendor_data.get("name", "Unknown")}
        )
    except HTTPException:
        # Re-raise HTTP exceptions to preserve status codes and messages
        raise
    except Exception as e:
        # Handle vendor not found scenarios that might be caught at service level
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Vendor not found")
        # Handle constraint violations, dependency errors, and other database issues
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{vendor_id}/purchase-orders", response_model=APIResponse)
async def get_vendor_purchase_orders(vendor_id: str):
    """
    Retrieve all purchase orders associated with a specific vendor.
    
    This endpoint provides comprehensive purchase order retrieval for vendor
    relationship management, enabling users to view all procurement activity
    with a specific vendor for analysis and reporting purposes.
    
    Path Parameters:
        vendor_id (str): Unique identifier for the vendor
        
    Returns:
        APIResponse: Standardized response containing:
            - success: True if retrieval succeeded
            - message: Descriptive success message
            - data: List of purchase order objects for the vendor
            
    Raises:
        HTTPException:
            - 404 error if vendor not found
            - 500 error for database or processing failures
            
    Business Logic:
        1. Validate vendor existence before querying purchase orders
        2. Retrieve all purchase orders with matching vendor_id
        3. Return complete purchase order list for relationship analysis
        4. Support empty list response if no purchase orders exist
        
    Use Cases:
        - Vendor performance analysis
        - Purchase history review
        - Relationship management
        - Compliance and audit reporting
    """
    try:
        # Validate vendor existence before querying related purchase orders
        # This ensures we return 404 for invalid vendors vs empty lists for valid vendors with no POs
        vendor_data = await db_service.get_vendor(vendor_id)
        if not vendor_data:
            raise HTTPException(status_code=404, detail="Vendor not found")
        
        # Retrieve all purchase orders associated with this vendor
        # The service layer handles filtering by vendor_id and returns complete PO data
        po_list = await db_service.list_purchase_orders(vendor_id_filter=vendor_id)
        
        # Return standardized success response with purchase order list
        # Empty list is a valid response for vendors with no purchase orders
        return APIResponse(
            success=True,
            message="Vendor purchase orders retrieved successfully",
            data=po_list
        )
    except HTTPException:
        # Re-raise HTTP exceptions to preserve status codes and messages
        raise
    except Exception as e:
        # Handle database connectivity issues and unexpected errors
        raise HTTPException(status_code=500, detail=str(e)) 