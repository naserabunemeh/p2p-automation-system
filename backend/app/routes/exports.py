from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime, timezone
from ..models import APIResponse, PaginatedResponse
from ..services.dynamodb_service import db_service
from ..services.s3_service import s3_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=PaginatedResponse)
async def list_exports(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    start_date: Optional[str] = Query(None, description="Filter files uploaded after this date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter files uploaded before this date (ISO format)"),
    vendor_id: Optional[str] = Query(None, description="Filter by vendor ID"),
    status: Optional[str] = Query(None, description="Filter by payment status"),
    file_type: Optional[str] = Query(None, description="Filter by file type (xml, json)")
):
    """
    List all S3 payment files (XML/JSON) with optional filters and pagination.
    Read-only endpoint for export dashboard.
    """
    try:
        # Validate file_type parameter if provided
        if file_type and file_type not in ['xml', 'json']:
            raise HTTPException(status_code=400, detail="file_type must be 'xml' or 'json'")
        
        # Get all payment files from S3 with filters
        files_result = await s3_service.list_all_payment_files(
            start_date=start_date,
            end_date=end_date,
            vendor_id=vendor_id,
            status=status,
            file_type=file_type
        )
        
        if not files_result.get('success'):
            raise HTTPException(status_code=500, detail=f"Failed to retrieve files from S3: {files_result.get('error', 'Unknown error')}")
        
        all_files = files_result.get('files', [])
        
        # Create audit log for exports list operation
        await db_service.create_audit_log(
            action="LIST_EXPORTS",
            entity_type="Export",
            entity_id="batch_operation",
            details={
                "filters_applied": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "vendor_id": vendor_id,
                    "status": status,
                    "file_type": file_type
                },
                "total_files_found": len(all_files),
                "page": page,
                "size": size
            },
            log_type="EXPORT_ACTION"
        )
        
        # Apply pagination
        total = len(all_files)
        start = (page - 1) * size
        end = start + size
        items = all_files[start:end]
        
        # Enrich each file with additional metadata for the response
        enriched_items = []
        for file_info in items:
            enriched_file = {
                **file_info,
                # Add computed fields for better UI experience
                'file_url': f"https://{s3_service.bucket_name}.s3.{s3_service.region_name}.amazonaws.com/{file_info['key']}",
                'download_url': f"/api/v1/exports/{file_info['payment_id']}/{file_info['file_type']}",
                'size_mb': round(file_info['size'] / (1024 * 1024), 2) if file_info['size'] > 0 else 0
            }
            enriched_items.append(enriched_file)
        
        return PaginatedResponse(
            items=enriched_items,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size if total > 0 else 0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing exports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list exports: {str(e)}")

@router.get("/{payment_id}/{file_type}")
async def download_export_file(payment_id: str, file_type: str):
    """
    Download a specific XML or JSON file for a payment.
    Uses S3 key stored in PaymentsTable.
    """
    try:
        # Validate file_type parameter
        if file_type not in ['xml', 'json']:
            raise HTTPException(status_code=400, detail="file_type must be 'xml' or 'json'")
        
        # Validate payment exists in DynamoDB
        payment = await db_service.get_payment(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Get the S3 key from payment record
        s3_key_field = f"{file_type}_s3_key"
        s3_key = payment.get(s3_key_field)
        
        if not s3_key:
            raise HTTPException(status_code=404, detail=f"{file_type.upper()} file not found for payment {payment_id}")
        
        # Retrieve file content from S3
        file_data = await s3_service.get_payment_file(s3_key)
        
        if not file_data.get('success'):
            raise HTTPException(status_code=500, detail=f"Failed to retrieve {file_type.upper()} file from S3: {file_data.get('error', 'Unknown error')}")
        
        # Create audit log for file download
        await db_service.create_audit_log(
            action="DOWNLOAD",
            entity_type="Export",
            entity_id=payment_id,
            details={
                "payment_id": payment_id,
                "file_type": file_type,
                "s3_key": s3_key,
                "file_size": len(file_data.get('content', '')),
                "vendor_id": payment.get('vendor_id'),
                "invoice_id": payment.get('invoice_id'),
                "amount": payment.get('amount')
            },
            log_type="EXPORT_ACTION"
        )
        
        # Return file content with appropriate headers
        media_type = f"application/{file_type}"
        filename = f"payment_{payment_id}.{file_type}"
        
        # Ensure datetime objects are serialized properly
        last_modified = file_data.get('last_modified', '')
        if hasattr(last_modified, 'isoformat'):
            last_modified = last_modified.isoformat()
        
        return JSONResponse(
            content={
                "success": True,
                "payment_id": payment_id,
                "file_type": file_type,
                "filename": filename,
                "content": file_data['content'],
                "content_type": media_type,
                "last_modified": last_modified,
                "file_key": s3_key,
                "metadata": file_data.get('metadata', {}),
                "download_timestamp": datetime.now(timezone.utc).isoformat()
            },
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Payment-ID": payment_id,
                "X-File-Type": file_type
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading {file_type} file for payment {payment_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}") 