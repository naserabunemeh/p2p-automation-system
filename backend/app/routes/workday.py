from fastapi import APIRouter, HTTPException
from typing import Literal
from pydantic import BaseModel
from datetime import datetime
from ..models import APIResponse
from ..services.dynamodb_service import db_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Request model for Workday callback
class WorkdayCallbackRequest(BaseModel):
    payment_id: str
    status: Literal["sent"] = "sent"

@router.post("/callback", response_model=APIResponse)
async def workday_callback(request: WorkdayCallbackRequest):
    """
    Simulates Workday confirming receipt of payment file.
    Updates payment status to 'sent' and creates audit log.
    """
    try:
        payment_id = request.payment_id
        new_status = request.status
        
        logger.info(f"Received Workday callback for payment {payment_id} with status {new_status}")
        
        # Validate payment exists
        payment = await db_service.get_payment(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
        
        # Get current status for audit trail
        current_status = payment.get('status', 'unknown')
        
        # Update payment status to 'sent'
        updated_payment = await db_service.update_payment(payment_id, {
            'status': new_status,
            'workday_confirmed_at': datetime.utcnow(),
            'workday_callback_received': True
        })
        
        # Create audit log with specific type for Workday callback
        await db_service.create_audit_log(
            action="CALLBACK_RECEIVED",
            entity_type="Payment",
            entity_id=payment_id,
            details={
                "payment_id": payment_id,
                "previous_status": current_status,
                "new_status": new_status,
                "workday_confirmed_at": datetime.utcnow().isoformat(),
                "invoice_id": payment.get('invoice_id'),
                "vendor_id": payment.get('vendor_id'),
                "amount": payment.get('amount'),
                "xml_s3_key": payment.get('xml_s3_key'),
                "json_s3_key": payment.get('json_s3_key'),
                "callback_source": "workday_simulation"
            },
            log_type="WORKDAY_CALLBACK"
        )
        
        logger.info(f"Payment {payment_id} status updated to '{new_status}' via Workday callback")
        
        return APIResponse(
            success=True,
            message=f"Payment {payment_id} status updated to '{new_status}' successfully",
            data={
                "payment_id": payment_id,
                "previous_status": current_status,
                "new_status": new_status,
                "workday_confirmed_at": updated_payment.get('workday_confirmed_at'),
                "callback_timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Workday callback for payment {request.payment_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process Workday callback: {str(e)}")

@router.get("/status/{payment_id}", response_model=APIResponse)
async def get_workday_status(payment_id: str):
    """
    Get Workday integration status for a payment.
    Useful for checking if callback was received.
    """
    try:
        # Validate payment exists
        payment = await db_service.get_payment(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
        
        # Create audit log for status check
        await db_service.create_audit_log(
            action="STATUS_CHECK",
            entity_type="Payment",
            entity_id=payment_id,
            details={
                "payment_id": payment_id,
                "current_status": payment.get('status'),
                "workday_callback_received": payment.get('workday_callback_received', False),
                "workday_confirmed_at": payment.get('workday_confirmed_at'),
                "xml_s3_key": payment.get('xml_s3_key'),
                "json_s3_key": payment.get('json_s3_key')
            },
            log_type="WORKDAY_CALLBACK"
        )
        
        workday_status = {
            "payment_id": payment_id,
            "current_status": payment.get('status'),
            "workday_callback_received": payment.get('workday_callback_received', False),
            "workday_confirmed_at": payment.get('workday_confirmed_at'),
            "xml_file_available": bool(payment.get('xml_s3_key')),
            "json_file_available": bool(payment.get('json_s3_key')),
            "integration_status": "confirmed" if payment.get('workday_callback_received') else "pending"
        }
        
        return APIResponse(
            success=True,
            message=f"Workday status retrieved for payment {payment_id}",
            data=workday_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Workday status for payment {payment_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get Workday status: {str(e)}") 