import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging
from decimal import Decimal
import json

logger = logging.getLogger(__name__)

class DynamoDBService:
    """Service class for DynamoDB operations"""
    
    def __init__(self, region_name: str = "us-east-1"):
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.region_name = region_name
        
        # Table references
        self.vendors_table = self.dynamodb.Table('VendorsTable')
        self.purchase_orders_table = self.dynamodb.Table('PurchaseOrdersTable')
        self.invoices_table = self.dynamodb.Table('InvoicesTable')
        self.payments_table = self.dynamodb.Table('PaymentsTable')
        self.audit_log_table = self.dynamodb.Table('AuditLogTable')
    
    def _convert_decimals(self, obj):
        """Convert Decimal objects to float for JSON serialization"""
        if isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(v) for v in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        else:
            return obj
    
    def _prepare_item_for_db(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare item for DynamoDB by converting datetime and other types"""
        prepared_item = {}
        for key, value in item.items():
            if value is None:
                continue  # Skip None values
            elif isinstance(value, datetime):
                prepared_item[key] = value.isoformat()
            elif isinstance(value, (int, float)):
                prepared_item[key] = Decimal(str(value))
            elif isinstance(value, list):
                prepared_item[key] = [self._prepare_item_for_db(v) if isinstance(v, dict) else v for v in value]
            elif isinstance(value, dict):
                prepared_item[key] = self._prepare_item_for_db(value)
            else:
                prepared_item[key] = value
        return prepared_item
    
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
    
    # Vendor operations
    async def create_vendor(self, vendor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new vendor in DynamoDB"""
        try:
            vendor_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            item = {
                'id': vendor_id,
                'created_at': now,
                'updated_at': now,
                **vendor_data
            }
            
            prepared_item = self._prepare_item_for_db(item)
            self.vendors_table.put_item(Item=prepared_item)
            
            logger.info(f"Created vendor with ID: {vendor_id}")
            return self._convert_item_from_db(prepared_item)
            
        except ClientError as e:
            logger.error(f"Error creating vendor: {e}")
            raise Exception(f"Failed to create vendor: {str(e)}")
    
    async def get_vendor(self, vendor_id: str) -> Optional[Dict[str, Any]]:
        """Get a vendor by ID"""
        try:
            response = self.vendors_table.get_item(Key={'id': vendor_id})
            
            if 'Item' not in response:
                return None
                
            return self._convert_item_from_db(response['Item'])
            
        except ClientError as e:
            logger.error(f"Error getting vendor {vendor_id}: {e}")
            raise Exception(f"Failed to get vendor: {str(e)}")
    
    async def update_vendor(self, vendor_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a vendor"""
        try:
            # First check if vendor exists
            existing_vendor = await self.get_vendor(vendor_id)
            if not existing_vendor:
                raise Exception("Vendor not found")
            
            # Prepare update expression
            update_data['updated_at'] = datetime.utcnow()
            prepared_data = self._prepare_item_for_db(update_data)
            
            update_expression = "SET "
            expression_attribute_values = {}
            expression_attribute_names = {}
            
            for key, value in prepared_data.items():
                attr_name = f"#{key}"
                attr_value = f":{key}"
                update_expression += f"{attr_name} = {attr_value}, "
                expression_attribute_names[attr_name] = key
                expression_attribute_values[attr_value] = value
            
            update_expression = update_expression.rstrip(", ")
            
            response = self.vendors_table.update_item(
                Key={'id': vendor_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="ALL_NEW"
            )
            
            logger.info(f"Updated vendor with ID: {vendor_id}")
            return self._convert_item_from_db(response['Attributes'])
            
        except ClientError as e:
            logger.error(f"Error updating vendor {vendor_id}: {e}")
            raise Exception(f"Failed to update vendor: {str(e)}")
    
    async def delete_vendor(self, vendor_id: str) -> bool:
        """Delete a vendor"""
        try:
            # First check if vendor exists
            existing_vendor = await self.get_vendor(vendor_id)
            if not existing_vendor:
                raise Exception("Vendor not found")
            
            self.vendors_table.delete_item(Key={'id': vendor_id})
            logger.info(f"Deleted vendor with ID: {vendor_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting vendor {vendor_id}: {e}")
            raise Exception(f"Failed to delete vendor: {str(e)}")
    
    async def list_vendors(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all vendors with optional status filter"""
        try:
            if status_filter:
                response = self.vendors_table.scan(
                    FilterExpression=boto3.dynamodb.conditions.Attr('status').eq(status_filter)
                )
            else:
                response = self.vendors_table.scan()
            
            items = [self._convert_item_from_db(item) for item in response.get('Items', [])]
            
            logger.info(f"Retrieved {len(items)} vendors")
            return items
            
        except ClientError as e:
            logger.error(f"Error listing vendors: {e}")
            raise Exception(f"Failed to list vendors: {str(e)}")
    
    # Purchase Order operations
    async def create_purchase_order(self, po_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new purchase order in DynamoDB"""
        try:
            po_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            item = {
                'id': po_id,
                'created_at': now,
                'updated_at': now,
                **po_data
            }
            
            prepared_item = self._prepare_item_for_db(item)
            self.purchase_orders_table.put_item(Item=prepared_item)
            
            # Create audit log entry
            await self.create_audit_log(
                action="CREATE",
                entity_type="PurchaseOrder",
                entity_id=po_id,
                details={
                    "vendor_id": po_data.get("vendor_id"),
                    "total_amount": po_data.get("total_amount"),
                    "status": po_data.get("status", "pending"),
                    "items_count": len(po_data.get("items", []))
                }
            )
            
            logger.info(f"Created purchase order with ID: {po_id}")
            return self._convert_item_from_db(prepared_item)
            
        except ClientError as e:
            logger.error(f"Error creating purchase order: {e}")
            raise Exception(f"Failed to create purchase order: {str(e)}")
    
    async def get_purchase_order(self, po_id: str) -> Optional[Dict[str, Any]]:
        """Get a purchase order by ID"""
        try:
            response = self.purchase_orders_table.get_item(Key={'id': po_id})
            
            if 'Item' not in response:
                return None
                
            return self._convert_item_from_db(response['Item'])
            
        except ClientError as e:
            logger.error(f"Error getting purchase order {po_id}: {e}")
            raise Exception(f"Failed to get purchase order: {str(e)}")
    
    async def update_purchase_order(self, po_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a purchase order"""
        try:
            # First check if PO exists
            existing_po = await self.get_purchase_order(po_id)
            if not existing_po:
                raise Exception("Purchase order not found")
            
            # Prepare update expression
            update_data['updated_at'] = datetime.utcnow()
            prepared_data = self._prepare_item_for_db(update_data)
            
            update_expression = "SET "
            expression_attribute_values = {}
            expression_attribute_names = {}
            
            for key, value in prepared_data.items():
                attr_name = f"#{key}"
                attr_value = f":{key}"
                update_expression += f"{attr_name} = {attr_value}, "
                expression_attribute_names[attr_name] = key
                expression_attribute_values[attr_value] = value
            
            update_expression = update_expression.rstrip(", ")
            
            response = self.purchase_orders_table.update_item(
                Key={'id': po_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="ALL_NEW"
            )
            
            # Create audit log entry
            await self.create_audit_log(
                action="UPDATE",
                entity_type="PurchaseOrder",
                entity_id=po_id,
                details={
                    "updated_fields": list(update_data.keys()),
                    "previous_status": existing_po.get("status"),
                    "new_status": update_data.get("status"),
                    "changes": update_data
                }
            )
            
            logger.info(f"Updated purchase order with ID: {po_id}")
            return self._convert_item_from_db(response['Attributes'])
            
        except ClientError as e:
            logger.error(f"Error updating purchase order {po_id}: {e}")
            raise Exception(f"Failed to update purchase order: {str(e)}")
    
    async def delete_purchase_order(self, po_id: str) -> bool:
        """Delete a purchase order"""
        try:
            # First check if PO exists
            existing_po = await self.get_purchase_order(po_id)
            if not existing_po:
                raise Exception("Purchase order not found")
            
            self.purchase_orders_table.delete_item(Key={'id': po_id})
            
            # Create audit log entry
            await self.create_audit_log(
                action="DELETE",
                entity_type="PurchaseOrder",
                entity_id=po_id,
                details={
                    "vendor_id": existing_po.get("vendor_id"),
                    "total_amount": existing_po.get("total_amount"),
                    "status": existing_po.get("status"),
                    "deleted_items": existing_po.get("items", [])
                }
            )
            
            logger.info(f"Deleted purchase order with ID: {po_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting purchase order {po_id}: {e}")
            raise Exception(f"Failed to delete purchase order: {str(e)}")
    
    async def list_purchase_orders(self, status_filter: Optional[str] = None, vendor_id_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all purchase orders with optional filters"""
        try:
            filter_expression = None
            
            if status_filter and vendor_id_filter:
                filter_expression = boto3.dynamodb.conditions.Attr('status').eq(status_filter) & boto3.dynamodb.conditions.Attr('vendor_id').eq(vendor_id_filter)
            elif status_filter:
                filter_expression = boto3.dynamodb.conditions.Attr('status').eq(status_filter)
            elif vendor_id_filter:
                filter_expression = boto3.dynamodb.conditions.Attr('vendor_id').eq(vendor_id_filter)
            
            if filter_expression:
                response = self.purchase_orders_table.scan(FilterExpression=filter_expression)
            else:
                response = self.purchase_orders_table.scan()
            
            items = [self._convert_item_from_db(item) for item in response.get('Items', [])]
            
            logger.info(f"Retrieved {len(items)} purchase orders")
            return items
            
        except ClientError as e:
            logger.error(f"Error listing purchase orders: {e}")
            raise Exception(f"Failed to list purchase orders: {str(e)}")
    
    # Audit logging operations
    async def create_audit_log(self, action: str, entity_type: str, entity_id: str, details: Dict[str, Any], user_id: Optional[str] = None, log_type: Optional[str] = None) -> Dict[str, Any]:
        """Create an audit log entry"""
        try:
            log_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            # Determine log type based on entity type if not provided
            if not log_type:
                if entity_type == "Invoice":
                    log_type = "INVOICE_ACTION"
                elif entity_type == "PurchaseOrder":
                    log_type = "PO_ACTION"
                else:
                    log_type = f"{entity_type.upper()}_ACTION"
            
            audit_entry = {
                'id': log_id,
                'type': log_type,
                'action': action,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'user_id': user_id or 'system',
                'timestamp': now,
                'details': details,
                'created_at': now
            }
            
            prepared_entry = self._prepare_item_for_db(audit_entry)
            self.audit_log_table.put_item(Item=prepared_entry)
            
            logger.info(f"Created audit log entry: {action} on {entity_type} {entity_id}")
            return self._convert_item_from_db(prepared_entry)
            
        except ClientError as e:
            logger.error(f"Error creating audit log: {e}")
            # Don't raise exception for audit logging failures to avoid breaking main operations
            return {}
    
    async def validate_vendor_exists(self, vendor_id: str) -> bool:
        """Validate that a vendor exists in the VendorsTable"""
        try:
            vendor = await self.get_vendor(vendor_id)
            return vendor is not None
        except Exception as e:
            logger.error(f"Error validating vendor {vendor_id}: {e}")
            return False
    
    # Invoice operations
    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new invoice in DynamoDB"""
        try:
            invoice_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            item = {
                'id': invoice_id,
                'created_at': now,
                'updated_at': now,
                'submitted_at': now,
                **invoice_data
            }
            
            prepared_item = self._prepare_item_for_db(item)
            self.invoices_table.put_item(Item=prepared_item)
            
            # Create audit log entry
            await self.create_audit_log(
                action="CREATE",
                entity_type="Invoice",
                entity_id=invoice_id,
                details={
                    "po_id": invoice_data.get("po_id"),
                    "invoice_number": invoice_data.get("invoice_number"),
                    "total_amount": invoice_data.get("total_amount"),
                    "status": invoice_data.get("status", "received"),
                    "items_count": len(invoice_data.get("items", []))
                }
            )
            
            logger.info(f"Created invoice with ID: {invoice_id}")
            return self._convert_item_from_db(prepared_item)
            
        except ClientError as e:
            logger.error(f"Error creating invoice: {e}")
            raise Exception(f"Failed to create invoice: {str(e)}")
    
    async def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Get an invoice by ID"""
        try:
            response = self.invoices_table.get_item(Key={'id': invoice_id})
            
            if 'Item' not in response:
                return None
                
            return self._convert_item_from_db(response['Item'])
            
        except ClientError as e:
            logger.error(f"Error getting invoice {invoice_id}: {e}")
            raise Exception(f"Failed to get invoice: {str(e)}")
    
    async def get_invoice_by_number(self, invoice_number: str) -> Optional[Dict[str, Any]]:
        """Get an invoice by invoice number"""
        try:
            response = self.invoices_table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('invoice_number').eq(invoice_number)
            )
            
            items = response.get('Items', [])
            if items:
                return self._convert_item_from_db(items[0])
            return None
            
        except ClientError as e:
            logger.error(f"Error getting invoice by number {invoice_number}: {e}")
            raise Exception(f"Failed to get invoice by number: {str(e)}")
    
    async def update_invoice(self, invoice_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an invoice"""
        try:
            # First check if invoice exists
            existing_invoice = await self.get_invoice(invoice_id)
            if not existing_invoice:
                raise Exception("Invoice not found")
            
            # Prepare update expression
            update_data['updated_at'] = datetime.utcnow()
            prepared_data = self._prepare_item_for_db(update_data)
            
            update_expression = "SET "
            expression_attribute_values = {}
            expression_attribute_names = {}
            
            for key, value in prepared_data.items():
                attr_name = f"#{key}"
                attr_value = f":{key}"
                update_expression += f"{attr_name} = {attr_value}, "
                expression_attribute_names[attr_name] = key
                expression_attribute_values[attr_value] = value
            
            update_expression = update_expression.rstrip(", ")
            
            response = self.invoices_table.update_item(
                Key={'id': invoice_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="ALL_NEW"
            )
            
            # Create audit log entry
            await self.create_audit_log(
                action="UPDATE",
                entity_type="Invoice",
                entity_id=invoice_id,
                details={
                    "updated_fields": list(update_data.keys()),
                    "previous_status": existing_invoice.get("status"),
                    "new_status": update_data.get("status"),
                    "changes": update_data
                }
            )
            
            logger.info(f"Updated invoice with ID: {invoice_id}")
            return self._convert_item_from_db(response['Attributes'])
            
        except ClientError as e:
            logger.error(f"Error updating invoice {invoice_id}: {e}")
            raise Exception(f"Failed to update invoice: {str(e)}")
    
    async def delete_invoice(self, invoice_id: str) -> bool:
        """Delete an invoice"""
        try:
            # First check if invoice exists
            existing_invoice = await self.get_invoice(invoice_id)
            if not existing_invoice:
                raise Exception("Invoice not found")
            
            self.invoices_table.delete_item(Key={'id': invoice_id})
            
            # Create audit log entry
            await self.create_audit_log(
                action="DELETE",
                entity_type="Invoice",
                entity_id=invoice_id,
                details={
                    "po_id": existing_invoice.get("po_id"),
                    "invoice_number": existing_invoice.get("invoice_number"),
                    "total_amount": existing_invoice.get("total_amount"),
                    "status": existing_invoice.get("status"),
                    "deleted_items": existing_invoice.get("items", [])
                }
            )
            
            logger.info(f"Deleted invoice with ID: {invoice_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting invoice {invoice_id}: {e}")
            raise Exception(f"Failed to delete invoice: {str(e)}")
    
    async def list_invoices(self, po_id_filter: Optional[str] = None, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all invoices with optional filters"""
        try:
            filter_expression = None
            
            if po_id_filter and status_filter:
                filter_expression = boto3.dynamodb.conditions.Attr('po_id').eq(po_id_filter) & boto3.dynamodb.conditions.Attr('status').eq(status_filter)
            elif po_id_filter:
                filter_expression = boto3.dynamodb.conditions.Attr('po_id').eq(po_id_filter)
            elif status_filter:
                filter_expression = boto3.dynamodb.conditions.Attr('status').eq(status_filter)
            
            if filter_expression:
                response = self.invoices_table.scan(FilterExpression=filter_expression)
            else:
                response = self.invoices_table.scan()
            
            items = [self._convert_item_from_db(item) for item in response.get('Items', [])]
            
            logger.info(f"Retrieved {len(items)} invoices")
            return items
            
        except ClientError as e:
            logger.error(f"Error listing invoices: {e}")
            raise Exception(f"Failed to list invoices: {str(e)}")
    
    async def reconcile_invoice_with_po(self, invoice_id: str, invoice_data: Dict[str, Any], po_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced Invoice Validation Logic - Part B
        Match invoice items and total_amount to the corresponding PO
        """
        try:
            reconciliation_details = {
                "total_amount_match": False,
                "items_match": False,
                "po_status_valid": False,
                "detailed_item_analysis": [],
                "discrepancies": []
            }
            
            logger.info(f"Starting invoice reconciliation for Invoice {invoice_id} with PO {po_data.get('id')}")
            
            # 1. Check if PO is in a valid status for reconciliation
            po_status = po_data.get("status", "").lower()
            if po_status in ["approved", "sent"]:
                reconciliation_details["po_status_valid"] = True
                logger.info(f"PO status validation passed: {po_status}")
            else:
                reconciliation_details["discrepancies"].append(f"PO status is '{po_status}', expected 'approved' or 'sent'")
                logger.warning(f"PO status validation failed: {po_status}")
            
            # 2. Enhanced total amount validation with detailed reporting
            po_total = float(po_data.get("total_amount", 0))
            invoice_total = float(invoice_data.get("total_amount", 0))
            amount_tolerance = po_total * 0.01  # 1% tolerance
            amount_difference = abs(po_total - invoice_total)
            
            if amount_difference <= amount_tolerance:
                reconciliation_details["total_amount_match"] = True
                logger.info(f"Total amount validation passed: PO=${po_total:.2f}, Invoice=${invoice_total:.2f}, Diff=${amount_difference:.2f}")
            else:
                reconciliation_details["discrepancies"].append(
                    f"Total amount mismatch: PO ${po_total:.2f}, Invoice ${invoice_total:.2f} (Difference: ${amount_difference:.2f}, Tolerance: ${amount_tolerance:.2f})"
                )
                logger.warning(f"Total amount validation failed: difference ${amount_difference:.2f} exceeds tolerance ${amount_tolerance:.2f}")
            
            # 3. Enhanced items validation with detailed item-by-item analysis
            po_items = po_data.get("items", [])
            invoice_items = invoice_data.get("items", [])
            
            # Basic count check
            if len(po_items) == len(invoice_items):
                reconciliation_details["items_match"] = True
                logger.info(f"Item count validation passed: {len(po_items)} items")
                
                # Detailed item analysis (if counts match)
                for i, (po_item, inv_item) in enumerate(zip(po_items, invoice_items)):
                    item_analysis = {
                        "line_number": i + 1,
                        "po_item": po_item,
                        "invoice_item": inv_item,
                        "match_status": "matched"
                    }
                    
                    # Check individual item details if available
                    po_qty = po_item.get("quantity", 0)
                    inv_qty = inv_item.get("quantity", 0)
                    po_price = po_item.get("unit_price", 0)
                    inv_price = inv_item.get("unit_price", 0)
                    
                    if po_qty != inv_qty:
                        item_analysis["match_status"] = "quantity_mismatch"
                        item_analysis["quantity_difference"] = f"PO: {po_qty}, Invoice: {inv_qty}"
                    
                    if abs(float(po_price) - float(inv_price)) > 0.01:  # Allow small floating point differences
                        item_analysis["match_status"] = "price_mismatch"
                        item_analysis["price_difference"] = f"PO: ${po_price}, Invoice: ${inv_price}"
                    
                    reconciliation_details["detailed_item_analysis"].append(item_analysis)
                    
            else:
                reconciliation_details["items_match"] = False
                reconciliation_details["discrepancies"].append(
                    f"Item count mismatch: PO has {len(po_items)} items, Invoice has {len(invoice_items)} items"
                )
                logger.warning(f"Item count validation failed: PO={len(po_items)}, Invoice={len(invoice_items)}")
            
            # 4. Determine final reconciliation status
            all_checks_passed = (
                reconciliation_details["total_amount_match"] and
                reconciliation_details["items_match"] and
                reconciliation_details["po_status_valid"]
            )
            
            if all_checks_passed:
                status = "matched"
                message = "Invoice successfully matched with purchase order - all validation checks passed"
                logger.info(f"Invoice {invoice_id} reconciliation successful")
            else:
                status = "rejected"
                discrepancy_count = len(reconciliation_details['discrepancies'])
                message = f"Invoice rejected due to {discrepancy_count} validation discrepancies"
                logger.warning(f"Invoice {invoice_id} reconciliation failed with {discrepancy_count} discrepancies")
            
            # 5. Create comprehensive audit log entry for reconciliation
            await self.create_audit_log(
                action="RECONCILE",
                entity_type="Invoice",
                entity_id=invoice_id,
                details={
                    "po_id": po_data.get("id"),
                    "invoice_number": invoice_data.get("invoice_number"),
                    "reconciliation_status": status,
                    "validation_summary": {
                        "po_status_valid": reconciliation_details["po_status_valid"],
                        "total_amount_match": reconciliation_details["total_amount_match"],
                        "items_match": reconciliation_details["items_match"],
                        "po_total": po_total,
                        "invoice_total": invoice_total,
                        "amount_difference": amount_difference,
                        "tolerance_used": amount_tolerance,
                        "item_counts": {"po": len(po_items), "invoice": len(invoice_items)}
                    },
                    "detailed_analysis": reconciliation_details["detailed_item_analysis"],
                    "discrepancies": reconciliation_details["discrepancies"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "status": status,
                "message": message,
                "details": reconciliation_details
            }
            
        except Exception as e:
            logger.error(f"Error reconciling invoice {invoice_id}: {e}")
            # Log the error as well
            await self.create_audit_log(
                action="RECONCILE_ERROR",
                entity_type="Invoice",
                entity_id=invoice_id,
                details={
                    "error": str(e),
                    "po_id": po_data.get("id", "unknown"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            raise Exception(f"Failed to reconcile invoice: {str(e)}")

# Global service instance
db_service = DynamoDBService() 