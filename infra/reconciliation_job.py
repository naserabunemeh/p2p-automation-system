#!/usr/bin/env python3
"""
Invoice Reconciliation Job - EventBridge Ready

This script can be run as:
1. Standalone CLI script: python reconciliation_job.py --region us-east-1 --dry-run
2. AWS Lambda function (triggered by EventBridge)

Purpose:
- Scans InvoicesTable for invoices with status == "received"
- Runs reconciliation logic against associated POs
- Updates invoice status to "matched" or "rejected"
- Logs all results to AuditLogTable

Future Integration:
- AWS EventBridge scheduled trigger (every 30 minutes)
- Lambda function deployment for serverless execution
"""

import argparse
import boto3
import json
import sys
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('reconciliation_job.log')
    ]
)
logger = logging.getLogger(__name__)


class ReconciliationJobService:
    """Service class for invoice reconciliation job operations"""
    
    def __init__(self, region_name: str = "us-east-1", dry_run: bool = False):
        self.region_name = region_name
        self.dry_run = dry_run
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        
        # Table references
        self.invoices_table = self.dynamodb.Table('InvoicesTable')
        self.purchase_orders_table = self.dynamodb.Table('PurchaseOrdersTable')
        self.audit_log_table = self.dynamodb.Table('AuditLogTable')
        
        # Job statistics
        self.stats = {
            "processed": 0,
            "matched": 0,
            "rejected": 0,
            "errors": 0,
            "skipped": 0
        }
        
        logger.info(f"Initialized ReconciliationJobService (region: {region_name}, dry_run: {dry_run})")
    
    def _convert_decimals(self, obj):
        """Convert Decimal objects to float for JSON serialization"""
        if isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(v) for v in obj]
        elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'Decimal':
            return float(obj)
        else:
            return obj
    
    def _convert_item_from_db(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert item from DynamoDB format to application format"""
        converted_item = {}
        for key, value in item.items():
            if isinstance(value, str) and key.endswith('_at'):
                try:
                    converted_item[key] = datetime.fromisoformat(value)
                except ValueError:
                    converted_item[key] = value
            else:
                converted_item[key] = self._convert_decimals(value)
        return converted_item
    
    async def create_audit_log(self, action: str, entity_type: str, entity_id: str, details: Dict[str, Any]) -> bool:
        """Create an audit log entry"""
        try:
            if self.dry_run:
                logger.info(f"[DRY RUN] Would create audit log: {action} on {entity_type} {entity_id}")
                return True
            
            log_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            audit_entry = {
                'id': log_id,
                'type': 'INVOICE_ACTION',
                'action': action,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'user_id': 'reconciliation_job',
                'timestamp': now.isoformat(),
                'details': details,
                'created_at': now.isoformat()
            }
            
            self.audit_log_table.put_item(Item=audit_entry)
            logger.info(f"Created audit log entry: {action} on {entity_type} {entity_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error creating audit log: {e}")
            return False
    
    def scan_received_invoices(self) -> List[Dict[str, Any]]:
        """Scan InvoicesTable for invoices with status == 'received'"""
        try:
            logger.info("Scanning InvoicesTable for received invoices...")
            
            response = self.invoices_table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('status').eq('received')
            )
            
            items = [self._convert_item_from_db(item) for item in response.get('Items', [])]
            logger.info(f"Found {len(items)} invoices with status 'received'")
            
            return items
            
        except ClientError as e:
            logger.error(f"Error scanning invoices: {e}")
            return []
    
    def get_purchase_order(self, po_id: str) -> Optional[Dict[str, Any]]:
        """Get a purchase order by ID"""
        try:
            response = self.purchase_orders_table.get_item(Key={'id': po_id})
            
            if 'Item' not in response:
                logger.warning(f"Purchase order not found: {po_id}")
                return None
                
            return self._convert_item_from_db(response['Item'])
            
        except ClientError as e:
            logger.error(f"Error getting purchase order {po_id}: {e}")
            return None
    
    def reconcile_invoice_with_po(self, invoice_data: Dict[str, Any], po_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced reconciliation logic for batch processing"""
        try:
            invoice_id = invoice_data.get('id')
            reconciliation_details = {
                "total_amount_match": False,
                "items_match": False,
                "po_status_valid": False,
                "discrepancies": []
            }
            
            # 1. Check PO status
            po_status = po_data.get("status", "").lower()
            if po_status in ["approved", "sent"]:
                reconciliation_details["po_status_valid"] = True
            else:
                reconciliation_details["discrepancies"].append(f"PO status is '{po_status}', expected 'approved' or 'sent'")
            
            # 2. Check total amount match (1% tolerance)
            po_total = float(po_data.get("total_amount", 0))
            invoice_total = float(invoice_data.get("total_amount", 0))
            amount_tolerance = po_total * 0.01
            amount_difference = abs(po_total - invoice_total)
            
            if amount_difference <= amount_tolerance:
                reconciliation_details["total_amount_match"] = True
            else:
                reconciliation_details["discrepancies"].append(
                    f"Total amount mismatch: PO ${po_total:.2f}, Invoice ${invoice_total:.2f} (Difference: ${amount_difference:.2f})"
                )
            
            # 3. Check items count
            po_items = po_data.get("items", [])
            invoice_items = invoice_data.get("items", [])
            
            if len(po_items) == len(invoice_items):
                reconciliation_details["items_match"] = True
            else:
                reconciliation_details["discrepancies"].append(
                    f"Item count mismatch: PO has {len(po_items)} items, Invoice has {len(invoice_items)} items"
                )
            
            # 4. Determine status
            all_checks_passed = (
                reconciliation_details["total_amount_match"] and
                reconciliation_details["items_match"] and
                reconciliation_details["po_status_valid"]
            )
            
            status = "matched" if all_checks_passed else "rejected"
            message = "Successfully matched" if all_checks_passed else f"Rejected due to {len(reconciliation_details['discrepancies'])} discrepancies"
            
            return {
                "status": status,
                "message": message,
                "details": reconciliation_details,
                "po_total": po_total,
                "invoice_total": invoice_total,
                "amount_difference": amount_difference
            }
            
        except Exception as e:
            logger.error(f"Error in reconciliation logic: {e}")
            return {
                "status": "rejected",
                "message": f"Reconciliation error: {str(e)}",
                "details": {"discrepancies": [f"System error: {str(e)}"]}
            }
    
    def update_invoice_status(self, invoice_id: str, new_status: str) -> bool:
        """Update invoice status in DynamoDB"""
        try:
            if self.dry_run:
                logger.info(f"[DRY RUN] Would update invoice {invoice_id} status to '{new_status}'")
                return True
            
            self.invoices_table.update_item(
                Key={'id': invoice_id},
                UpdateExpression="SET #status = :status, updated_at = :updated_at",
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': new_status,
                    ':updated_at': datetime.now(timezone.utc).isoformat()
                }
            )
            
            logger.info(f"Updated invoice {invoice_id} status to '{new_status}'")
            return True
            
        except ClientError as e:
            logger.error(f"Error updating invoice {invoice_id}: {e}")
            return False
    
    async def process_invoice(self, invoice_data: Dict[str, Any]) -> bool:
        """Process a single invoice for reconciliation"""
        invoice_id = invoice_data.get('id')
        po_id = invoice_data.get('po_id')
        invoice_number = invoice_data.get('invoice_number', 'Unknown')
        
        try:
            logger.info(f"Processing invoice {invoice_id} (#{invoice_number}) with PO {po_id}")
            
            # Get associated PO
            po_data = self.get_purchase_order(po_id)
            if not po_data:
                self.stats["errors"] += 1
                await self.create_audit_log(
                    action="RECONCILE_ERROR",
                    entity_type="Invoice",
                    entity_id=invoice_id,
                    details={
                        "error": f"Associated PO {po_id} not found",
                        "invoice_number": invoice_number,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                return False
            
            # Run reconciliation
            reconciliation_result = self.reconcile_invoice_with_po(invoice_data, po_data)
            new_status = reconciliation_result["status"]
            
            # Update invoice status
            if self.update_invoice_status(invoice_id, new_status):
                # Log reconciliation result
                await self.create_audit_log(
                    action="BATCH_RECONCILE",
                    entity_type="Invoice",
                    entity_id=invoice_id,
                    details={
                        "po_id": po_id,
                        "invoice_number": invoice_number,
                        "reconciliation_status": new_status,
                        "message": reconciliation_result["message"],
                        "validation_summary": {
                            "po_status_valid": reconciliation_result["details"]["po_status_valid"],
                            "total_amount_match": reconciliation_result["details"]["total_amount_match"],
                            "items_match": reconciliation_result["details"]["items_match"],
                            "po_total": reconciliation_result.get("po_total", 0),
                            "invoice_total": reconciliation_result.get("invoice_total", 0),
                            "amount_difference": reconciliation_result.get("amount_difference", 0)
                        },
                        "discrepancies": reconciliation_result["details"]["discrepancies"],
                        "processed_by": "reconciliation_job",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
                # Update statistics
                self.stats["processed"] += 1
                if new_status == "matched":
                    self.stats["matched"] += 1
                else:
                    self.stats["rejected"] += 1
                
                logger.info(f"Successfully processed invoice {invoice_id}: {new_status}")
                return True
            else:
                self.stats["errors"] += 1
                return False
                
        except Exception as e:
            logger.error(f"Error processing invoice {invoice_id}: {e}")
            self.stats["errors"] += 1
            await self.create_audit_log(
                action="RECONCILE_ERROR",
                entity_type="Invoice",
                entity_id=invoice_id,
                details={
                    "error": str(e),
                    "invoice_number": invoice_number,
                    "po_id": po_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            return False
    
    async def run_reconciliation_job(self) -> Dict[str, Any]:
        """Main reconciliation job execution"""
        start_time = datetime.now(timezone.utc)
        logger.info(f"Starting invoice reconciliation job at {start_time.isoformat()}")
        
        if self.dry_run:
            logger.info("[DRY RUN MODE] - No changes will be made")
        
        try:
            # Scan for received invoices
            received_invoices = self.scan_received_invoices()
            
            if not received_invoices:
                logger.info("No invoices with status 'received' found. Job completed.")
                return {
                    "success": True,
                    "message": "No invoices to process",
                    "statistics": self.stats,
                    "execution_time": 0
                }
            
            # Process each invoice
            logger.info(f"Processing {len(received_invoices)} received invoices...")
            
            for invoice in received_invoices:
                await self.process_invoice(invoice)
            
            # Calculate execution time
            end_time = datetime.now(timezone.utc)
            execution_time = (end_time - start_time).total_seconds()
            
            # Log job completion
            await self.create_audit_log(
                action="JOB_COMPLETE",
                entity_type="ReconciliationJob",
                entity_id=f"job_{start_time.strftime('%Y%m%d_%H%M%S')}",
                details={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "execution_time_seconds": execution_time,
                    "statistics": self.stats,
                    "dry_run": self.dry_run,
                    "region": self.region_name
                }
            )
            
            logger.info(f"Reconciliation job completed in {execution_time:.2f} seconds")
            logger.info(f"Statistics: {json.dumps(self.stats, indent=2)}")
            
            return {
                "success": True,
                "message": "Reconciliation job completed successfully",
                "statistics": self.stats,
                "execution_time": execution_time
            }
            
        except Exception as e:
            logger.error(f"Reconciliation job failed: {e}")
            return {
                "success": False,
                "message": f"Job failed: {str(e)}",
                "statistics": self.stats
            }


def lambda_handler(event, context):
    """AWS Lambda entry point for EventBridge triggers"""
    logger.info("Lambda function started via EventBridge trigger")
    
    # Extract region from Lambda context or default
    region = context.aws_region if hasattr(context, 'aws_region') else 'us-east-1'
    
    # Initialize reconciliation service
    reconciliation_service = ReconciliationJobService(region_name=region, dry_run=False)
    
    # Run the job
    import asyncio
    result = asyncio.run(reconciliation_service.run_reconciliation_job())
    
    # Return Lambda-compatible response
    return {
        'statusCode': 200 if result["success"] else 500,
        'body': json.dumps(result),
        'headers': {
            'Content-Type': 'application/json'
        }
    }


async def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Invoice Reconciliation Job - EventBridge Ready",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python reconciliation_job.py --region us-east-1 --dry-run
  python reconciliation_job.py --region us-west-2
  python reconciliation_job.py --help

This script processes invoices with status 'received' and runs reconciliation
against their associated purchase orders. Results are logged to AuditLogTable.
        """
    )
    
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no changes made)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Set log level
    logger.setLevel(getattr(logging, args.log_level))
    
    # Initialize and run reconciliation service
    reconciliation_service = ReconciliationJobService(
        region_name=args.region,
        dry_run=args.dry_run
    )
    
    result = await reconciliation_service.run_reconciliation_job()
    
    # Exit with appropriate code
    exit_code = 0 if result["success"] else 1
    if not result["success"]:
        logger.error(f"Job failed: {result['message']}")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 