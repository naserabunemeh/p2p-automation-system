from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
from ..models import Payment, PaymentCreate, PaymentUpdate, APIResponse, PaginatedResponse
from ..services.dynamodb_service import db_service
from ..services.s3_service import s3_service
from ..services.xml_generator import XMLGenerator
from datetime import datetime
import uuid
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Request models for specific endpoints
class ApprovePaymentRequest(BaseModel):
    approved_by: str

@router.get("/", response_model=PaginatedResponse)
async def list_payments(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status (approved, sent, failed)"),
    vendor_id: Optional[str] = Query(None, description="Filter by vendor ID"),
    invoice_id: Optional[str] = Query(None, description="Filter by invoice ID")
):
    """List all payments with pagination and optional filters"""
    try:
        # Get payments from DynamoDB with filters
        payments = await db_service.list_payments(
            status_filter=status,
            vendor_id_filter=vendor_id,
            invoice_id_filter=invoice_id
        )
        
        # Create audit log for payment list operation
        await db_service.create_audit_log(
            action="LIST",
            entity_type="Payment",
            entity_id="batch_operation",
            details={
                "filters_applied": {
                    "status": status,
                    "vendor_id": vendor_id,
                    "invoice_id": invoice_id
                },
                "results_count": len(payments),
                "page": page,
                "size": size
            },
            log_type="PAYMENT_ACTION"
        )
        
        # Apply pagination
        total = len(payments)
        start = (page - 1) * size
        end = start + size
        items = payments[start:end]
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size if total > 0 else 0
        )
        
    except Exception as e:
        logger.error(f"Error listing payments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list payments: {str(e)}")

@router.post("/{invoice_id}/approve", response_model=APIResponse)
async def approve_payment(invoice_id: str, request: ApprovePaymentRequest):
    """
    Approve a reconciled invoice and create a payment record.
    Generates Workday-compatible XML and JSON files and uploads to S3.
    """
    try:
        logger.info(f"Starting payment approval process for invoice {invoice_id}")
        
        # Step 1: Approve invoice and create payment record
        payment = await db_service.approve_invoice_and_create_payment(
            invoice_id=invoice_id,
            approved_by=request.approved_by
        )
        
        # Step 2: Get related data for complete payment information
        invoice = await db_service.get_invoice(invoice_id)
        vendor = await db_service.get_vendor(payment['vendor_id'])
        
        # Enhance payment data with related information
        enhanced_payment = {
            **payment,
            'vendor_name': vendor.get('name') if vendor else 'Unknown Vendor',
            'vendor_email': vendor.get('email') if vendor else '',
            'invoice_number': invoice.get('invoice_number') if invoice else '',
            'invoice_date': invoice.get('invoice_date') if invoice else None,
            'due_date': invoice.get('due_date') if invoice else None
        }
        
        # Step 3: Generate XML content using XMLGenerator (Workday-compatible)
        xml_content = XMLGenerator.generate_payment_xml(enhanced_payment)
        
        # Step 4: Generate JSON content (mirror of XML structure)
        json_content = XMLGenerator.generate_payment_json(enhanced_payment)
        
        # Step 5: Upload XML file to S3
        xml_upload_result = await s3_service.upload_payment_file(
            payment_id=payment['id'],
            content=xml_content,
            file_format='xml',
            payment_data=enhanced_payment
        )
        
        # Step 6: Upload JSON file to S3
        json_upload_result = await s3_service.upload_payment_file(
            payment_id=payment['id'],
            content=json_content,
            file_format='json',
            payment_data=enhanced_payment
        )
        
        # Step 7: Update payment with S3 file information
        update_data = {}
        if xml_upload_result.get('success'):
            update_data['xml_s3_key'] = xml_upload_result.get('key')
        if json_upload_result.get('success'):
            update_data['json_s3_key'] = json_upload_result.get('key')
        
        if update_data:
            payment = await db_service.update_payment(payment['id'], update_data)
        
        # Step 8: Create simplified audit log for payment approval with S3 file references
        try:
            await db_service.create_audit_log(
                action="APPROVE_WITH_FILES",
                entity_type="Payment", 
                entity_id=payment['id'],
                details={
                    "invoice_id": invoice_id,
                    "vendor_id": str(payment['vendor_id']),
                    "amount": str(payment['amount']),
                    "status": str(payment['status']),
                    "approved_by": str(request.approved_by),
                    "xml_s3_key": str(payment.get('xml_s3_key', '')),
                    "json_s3_key": str(payment.get('json_s3_key', '')),
                    "files_generated": "xml,json"
                },
                log_type="PAYMENT_ACTION"
            )
        except Exception as audit_error:
            logger.error(f"Failed to create payment approval audit log: {audit_error}")
        
        # Step 9: Prepare response
        response_data = {
            'payment': enhanced_payment,
            'files_generated': {
                'xml': xml_upload_result,
                'json': json_upload_result
            },
            'invoice_id': invoice_id,
            'approved_by': request.approved_by,
            'approval_timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Payment approval completed for invoice {invoice_id}, payment {payment['id']}")
        
        return APIResponse(
            success=True,
            message=f"Invoice {invoice_id} approved and payment {payment['id']} created successfully. XML and JSON files uploaded to S3.",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error approving payment for invoice {invoice_id}: {e}")
        if "Invoice not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        elif "Cannot approve invoice" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=f"Failed to approve payment: {str(e)}")

@router.get("/{payment_id}", response_model=APIResponse)
async def get_payment(payment_id: str):
    """Get a payment by ID"""
    try:
        logger.info(f"API GET payment {payment_id}: Starting...")
        
        payment = await db_service.get_payment(payment_id)
        logger.info(f"API GET payment {payment_id}: get_payment returned: {payment is not None}")
        
        if not payment:
            logger.warning(f"API GET payment {payment_id}: Payment not found")
            raise HTTPException(status_code=404, detail="Payment not found")
        
        logger.info(f"API GET payment {payment_id}: Payment found with keys: {list(payment.keys())}")
        
        # Get related S3 files if they exist
        s3_files = None
        if payment.get('xml_s3_key') or payment.get('json_s3_key'):
            s3_files = await s3_service.list_payment_files(payment_id)
        
        response_data = {
            'payment': payment,
            's3_files': s3_files
        }
        
        # Create audit log for payment retrieval - temporarily disabled for debugging
        try:
            await db_service.create_audit_log(
                action="READ",
                entity_type="Payment",
                entity_id=payment_id,
                details={
                    "invoice_id": payment.get("invoice_id"),
                    "vendor_id": payment.get("vendor_id"),
                    "amount": str(payment.get("amount")),
                    "status": payment.get("status"),
                    "xml_s3_key": payment.get("xml_s3_key", ""),
                    "json_s3_key": payment.get("json_s3_key", "")
                },
                log_type="PAYMENT_ACTION"
            )
        except Exception as audit_error:
            logger.warning(f"Audit logging failed for payment {payment_id}: {audit_error}")
            # Don't fail the entire request if audit logging fails
        
        return APIResponse(
            success=True,
            message="Payment retrieved successfully",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"API GET payment {payment_id}: Exception occurred: {e}")
        import traceback
        logger.error(f"API GET payment {payment_id}: Full traceback: {traceback.format_exc()}")
        if "Payment not found" in str(e):
            raise HTTPException(status_code=404, detail=f"404: {str(e)}")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to get payment: {str(e)}")

@router.put("/{payment_id}", response_model=APIResponse)
async def update_payment(payment_id: str, payment_update: PaymentUpdate):
    """Update a payment"""
    try:
        # Validate payment exists
        existing_payment = await db_service.get_payment(payment_id)
        if not existing_payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Prepare update data
        update_data = payment_update.dict(exclude_unset=True)
        
        # Update payment in DynamoDB
        updated_payment = await db_service.update_payment(payment_id, update_data)
        
        # Additional audit log for route-level update with enhanced details
        await db_service.create_audit_log(
            action="UPDATE_VIA_API",
            entity_type="Payment",
            entity_id=payment_id,
            details={
                "invoice_id": updated_payment.get("invoice_id"),
                "vendor_id": updated_payment.get("vendor_id"),
                "amount": updated_payment.get("amount"),
                "status": updated_payment.get("status"),
                "xml_s3_key": updated_payment.get("xml_s3_key"),
                "json_s3_key": updated_payment.get("json_s3_key"),
                "fields_updated": list(update_data.keys()),
                "previous_status": existing_payment.get("status"),
                "new_status": updated_payment.get("status")
            },
            log_type="PAYMENT_ACTION"
        )
        
        return APIResponse(
            success=True,
            message="Payment updated successfully",
            data=updated_payment
        )
        
    except Exception as e:
        logger.error(f"Error updating payment {payment_id}: {e}")
        if "Payment not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=f"Failed to update payment: {str(e)}")

# Additional utility endpoints
@router.get("/{payment_id}/files", response_model=APIResponse)
async def get_payment_files(payment_id: str):
    """Get all S3 files for a payment"""
    try:
        # Validate payment exists
        payment = await db_service.get_payment(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Get S3 files
        files_info = await s3_service.list_payment_files(payment_id)
        
        return APIResponse(
            success=True,
            message=f"Retrieved {files_info.get('file_count', 0)} files for payment {payment_id}",
            data=files_info
        )
        
    except Exception as e:
        logger.error(f"Error getting files for payment {payment_id}: {e}")
        if "Payment not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=f"Failed to get payment files: {str(e)}")

@router.get("/{payment_id}/files/{file_format}")
async def download_payment_file(payment_id: str, file_format: str):
    """Download payment file (XML or JSON) from S3"""
    try:
        if file_format not in ['xml', 'json']:
            raise HTTPException(status_code=400, detail="File format must be 'xml' or 'json'")
        
        # Validate payment exists
        payment = await db_service.get_payment(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # List files to find the requested format
        files_info = await s3_service.list_payment_files(payment_id)
        
        if not files_info.get('success'):
            raise HTTPException(status_code=500, detail="Failed to retrieve file list from S3")
        
        # Find file with matching format
        target_file = None
        for file_info in files_info.get('files', []):
            if file_info['key'].endswith(f'.{file_format}'):
                target_file = file_info
                break
        
        if not target_file:
            raise HTTPException(status_code=404, detail=f"{file_format.upper()} file not found for payment {payment_id}")
        
        # Get file content from S3
        file_data = await s3_service.get_payment_file(target_file['key'])
        
        if not file_data.get('success'):
            raise HTTPException(status_code=500, detail=f"Failed to retrieve {file_format.upper()} file from S3")
        
        # Return file content with appropriate headers
        media_type = f"application/{file_format}"
        filename = f"payment_{payment_id}.{file_format}"
        
        return JSONResponse(
            content={
                "filename": filename,
                "content": file_data['content'],
                "content_type": media_type,
                "last_modified": file_data.get('last_modified', ''),
                "file_key": target_file['key']
            },
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error downloading {file_format} file for payment {payment_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}") 