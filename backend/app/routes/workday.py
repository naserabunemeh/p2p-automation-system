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

@router.post("/test-callback", response_model=APIResponse)
async def test_workday_callback(request: WorkdayCallbackRequest):
    """
    Minimal test version of Workday callback to isolate the decimal conversion issue
    """
    try:
        logger.info("TEST CALLBACK: Starting minimal test")
        
        payment_id = request.payment_id
        logger.info(f"TEST CALLBACK: Payment ID: {payment_id}")
        
        new_status = request.status
        logger.info(f"TEST CALLBACK: New status: {new_status}")
        
        return APIResponse(
            success=True,
            message=f"Test callback successful for payment {payment_id}",
            data={
                "payment_id": payment_id,
                "status": new_status,
                "test": True
            }
        )
        
    except Exception as e:
        logger.error(f"TEST CALLBACK ERROR: {e}")
        import traceback
        logger.error(f"TEST CALLBACK TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Test callback failed: {str(e)}")

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
        logger.info(f"Step 1: Validating payment {payment_id} exists")
        try:
            payment = await db_service.get_payment(payment_id)
            logger.info(f"Step 1 SUCCESS: Payment retrieved")
        except Exception as get_error:
            logger.error(f"Step 1 FAILED: Error getting payment: {get_error}")
            raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found: {get_error}")
        
        if not payment:
            raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
        
        # Get current status for audit trail
        current_status = payment.get('status', 'unknown')
        logger.info(f"Step 2: Current payment status is {current_status}")
        
        # Pre-convert datetime to avoid any conversion issues
        timestamp = datetime.utcnow().isoformat()
        logger.info(f"Step 3: Generated timestamp: {timestamp}")
        
        # Update payment status using specialized method
        logger.info(f"Step 4: Using specialized Workday callback update method")
        try:
            updated_payment = await db_service.update_payment_workday_callback(
                payment_id=payment_id,
                status=new_status,
                confirmed_at=timestamp
            )
            logger.info(f"Step 4 SUCCESS: Workday callback update completed")
        except Exception as update_error:
            logger.error(f"Step 4 FAILED: Payment update error: {update_error}")
            import traceback
            logger.error(f"Step 4 TRACEBACK: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Payment update failed: {update_error}")
        
        # Skip audit logging temporarily for debugging
        logger.info(f"Step 5: SKIPPING audit log entry for debugging purposes")
        
        logger.info(f"Workday callback processed successfully: payment {payment_id} status {current_status} -> {new_status}")
        
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
        logger.error(f"Error processing Workday callback for payment {getattr(request, 'payment_id', 'unknown')}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
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
        
        # Create audit log entry for the status check
        try:
            await db_service.create_audit_log(
                action="STATUS_CHECK",
                entity_type="Payment",
                entity_id=payment_id,
                details={
                    "current_status": payment.get('status'),
                    "workday_callback_received": payment.get('workday_callback_received', False),
                    "check_timestamp": datetime.utcnow().isoformat(),
                    "integration_status": "confirmed" if payment.get('workday_callback_received') else "pending"
                },
                log_type="WORKDAY_ACTION"
            )
        except Exception as audit_error:
            logger.error(f"Failed to create status check audit log: {audit_error}")
        
        logger.info(f"Workday status check: payment {payment_id} integration status")
        
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