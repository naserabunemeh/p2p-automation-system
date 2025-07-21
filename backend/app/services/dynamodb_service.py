import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging
from decimal import Decimal
import decimal
import json

logger = logging.getLogger(__name__)

class DynamoDBService:
    """Service class for DynamoDB operations"""
    
    def __init__(self, region_name: str = "us-east-1"):
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.region_name = region_name
        
        # Table references
        self.vendors_table = self.dynamodb.Table('p2p_vendors')
        self.purchase_orders_table = self.dynamodb.Table('p2p_purchase_orders')
        self.invoices_table = self.dynamodb.Table('p2p_invoices')
        self.payments_table = self.dynamodb.Table('p2p_payments')
        # Note: AuditLogTable doesn't exist yet - will use basic logging for now
        # self.audit_log_table = self.dynamodb.Table('AuditLogTable')
    
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
        try:
            prepared_item = {}
            for key, value in item.items():
                try:
                    if value is None:
                        continue  # Skip None values
                    elif isinstance(value, bool):
                        prepared_item[key] = value  # Booleans are natively supported in DynamoDB
                    elif isinstance(value, datetime):
                        prepared_item[key] = value.isoformat()
                    elif isinstance(value, (int, float)):
                        try:
                            prepared_item[key] = Decimal(str(value))
                        except (ValueError, TypeError, decimal.ConversionSyntax):
                            logger.warning(f"Failed to convert {key}={value} to Decimal, keeping as string")
                            prepared_item[key] = str(value)
                    elif isinstance(value, str) and key in ['amount', 'total_amount', 'unit_price', 'quantity']:
                        # Handle numeric string fields that should be decimals
                        try:
                            prepared_item[key] = Decimal(str(value))
                        except (ValueError, TypeError, decimal.ConversionSyntax):
                            logger.warning(f"Failed to convert string {key}={value} to Decimal, keeping as string")
                            prepared_item[key] = value  # Keep as string if conversion fails
                    elif isinstance(value, list):
                        try:
                            prepared_item[key] = [self._prepare_item_for_db(v) if isinstance(v, dict) else str(v) for v in value]
                        except Exception as list_error:
                            logger.warning(f"Failed to process list {key}: {list_error}, converting to string")
                            prepared_item[key] = str(value)
                    elif isinstance(value, dict):
                        try:
                            prepared_item[key] = self._prepare_item_for_db(value)
                        except Exception as dict_error:
                            logger.warning(f"Failed to process dict {key}: {dict_error}, converting to string")
                            prepared_item[key] = str(value)
                    else:
                        # Handle enum values specially to use their .value property
                        if hasattr(value, 'value'):  # Check if it's an enum
                            prepared_item[key] = str(value.value)
                        else:
                            prepared_item[key] = str(value)  # Convert everything else to string to be safe
                except Exception as field_error:
                    logger.warning(f"Failed to process field {key}={value}: {field_error}, skipping")
                    continue
            return prepared_item
        except Exception as e:
            logger.error(f"Critical error in _prepare_item_for_db: {e}")
            # Return a safe fallback
            return {"error": "Failed to prepare item for database"}
    
    
    def _convert_item_from_db(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert item from DynamoDB format to application format"""
        converted_item = {}
        for key, value in item.items():
            if isinstance(value, str) and key.endswith('_at'):
                try:
                    converted_item[key] = datetime.fromisoformat(value)
                except ValueError:
                    converted_item[key] = value
            elif key == 'status' and isinstance(value, str):
                # Handle corrupted enum values stored as "EnumName.VALUE"
                if '.' in value and 'Status.' in value:
                    # Extract the actual enum value after the dot
                    enum_value = value.split('.')[-1].lower()
                    converted_item[key] = enum_value
                else:
                    converted_item[key] = self._convert_decimals(value)
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
            
            # Sanitize details to avoid decimal conversion issues
            sanitized_details = self._sanitize_audit_details(details)
            
            audit_entry = {
                'id': log_id,
                'type': log_type,
                'action': action,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'user_id': user_id or 'system',
                'timestamp': now,
                'details': sanitized_details,
                'created_at': now
            }
            
            prepared_entry = self._prepare_item_for_db(audit_entry)
            # self.audit_log_table.put_item(Item=prepared_entry)
            # Temporarily disabled audit logging - table doesn't exist
            logger.info(f"Audit log: {log_type} - {action} on {entity_type} {entity_id}")
            
            logger.info(f"Created audit log entry: {action} on {entity_type} {entity_id}")
            return self._convert_item_from_db(prepared_entry)
            
        except Exception as e:
            logger.error(f"Error creating audit log: {e}")
            # Don't raise exception for audit logging failures to avoid breaking main operations
            return {}

    def _sanitize_audit_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize audit details to prevent decimal conversion issues"""
        try:
            sanitized = {}
            for key, value in details.items():
                if value is None:
                    continue
                elif isinstance(value, (dict, list)):
                    # Convert complex structures to string to avoid decimal conversion issues
                    sanitized[key] = str(value)
                elif isinstance(value, (int, float, Decimal)):
                    sanitized[key] = str(value)
                else:
                    sanitized[key] = str(value)
            return sanitized
        except Exception as e:
            logger.error(f"Error sanitizing audit details: {e}")
            return {"error": "Failed to sanitize audit details"}
    
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
            
            # 5. Create simplified audit log entry for reconciliation
            try:
                await self.create_audit_log(
                    action="RECONCILE",
                    entity_type="Invoice",
                    entity_id=invoice_id,
                    details={
                        "po_id": po_data.get("id"),
                        "invoice_number": invoice_data.get("invoice_number"),
                        "reconciliation_status": status,
                        "po_total": str(po_total),
                        "invoice_total": str(invoice_total),
                        "amount_difference": str(amount_difference),
                        "discrepancy_count": len(reconciliation_details["discrepancies"]),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            except Exception as audit_error:
                logger.error(f"Failed to create reconciliation audit log: {audit_error}")
            
            return {
                "status": status,
                "message": message,
                "details": reconciliation_details
            }
            
        except Exception as e:
            import traceback
            logger.error(f"Error reconciling invoice {invoice_id}: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Log the error as well without complex details to avoid nested errors
            try:
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
            except Exception as audit_error:
                logger.error(f"Failed to create audit log for reconciliation error: {audit_error}")
            raise Exception(f"Failed to reconcile invoice: {str(e)}")

    # Payment operations  
    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new payment in DynamoDB"""
        try:
            payment_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            item = {
                'id': payment_id,
                'created_at': now,
                'updated_at': now,
                **payment_data
            }
            
            prepared_item = self._prepare_item_for_db(item)
            self.payments_table.put_item(Item=prepared_item)
            
            # Create audit log entry
            await self.create_audit_log(
                action="CREATE",
                entity_type="Payment",
                entity_id=payment_id,
                details={
                    "invoice_id": payment_data.get("invoice_id"),
                    "vendor_id": payment_data.get("vendor_id"),
                    "amount": payment_data.get("amount"),
                    "currency": payment_data.get("currency", "USD"),
                    "status": payment_data.get("status", "approved"),
                    "xml_s3_key": payment_data.get("xml_s3_key"),
                    "json_s3_key": payment_data.get("json_s3_key")
                },
                log_type="PAYMENT_ACTION"
            )
            
            logger.info(f"Created payment with ID: {payment_id}")
            return self._convert_item_from_db(prepared_item)
            
        except ClientError as e:
            logger.error(f"Error creating payment: {e}")
            raise Exception(f"Failed to create payment: {str(e)}")

    async def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get a payment by ID"""
        try:
            logger.info(f"Getting payment {payment_id} from DynamoDB...")
            response = self.payments_table.get_item(Key={'id': payment_id})
            
            logger.info(f"DynamoDB response keys: {list(response.keys())}")
            
            if 'Item' not in response:
                logger.warning(f"Payment {payment_id} not found in DynamoDB")
                return None
            
            raw_item = response['Item']
            logger.info(f"Raw item found with keys: {list(raw_item.keys())}")
            logger.info(f"Raw item status: {raw_item.get('status')}")
            
            try:
                converted_item = self._convert_item_from_db(raw_item)
                logger.info(f"Successfully converted payment {payment_id}")
                return converted_item
            except Exception as convert_error:
                logger.error(f"Error converting payment {payment_id} from DB: {convert_error}")
                import traceback
                logger.error(f"Conversion traceback: {traceback.format_exc()}")
                raise
            
        except ClientError as e:
            logger.error(f"Error getting payment {payment_id}: {e}")
            raise Exception(f"Failed to get payment: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting payment {payment_id}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

    async def update_payment(self, payment_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a payment"""
        try:
            # First check if payment exists
            existing_payment = await self.get_payment(payment_id)
            if not existing_payment:
                raise Exception("Payment not found")
            
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
            
            response = self.payments_table.update_item(
                Key={'id': payment_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="ALL_NEW"
            )
            
            # Create audit log entry
            try:
                await self.create_audit_log(
                    action="UPDATE",
                    entity_type="Payment",
                    entity_id=payment_id,
                    details={
                        "updated_fields": list(update_data.keys()),
                        "previous_status": existing_payment.get("status"),
                        "new_status": update_data.get("status")
                    },
                    log_type="PAYMENT_ACTION"
                )
            except Exception as audit_error:
                logger.error(f"Failed to create payment update audit log: {audit_error}")
                # Don't fail the update if audit logging fails
            
            logger.info(f"Updated payment with ID: {payment_id}")
            return self._convert_item_from_db(response['Attributes'])
            
        except ClientError as e:
            logger.error(f"Error updating payment {payment_id}: {e}")
            raise Exception(f"Failed to update payment: {str(e)}")

    async def update_payment_workday_callback(self, payment_id: str, status: str, confirmed_at: str) -> Dict[str, Any]:
        """
        Specialized update method for Workday callbacks that avoids decimal conversion issues
        """
        try:
            # Validate payment exists first
            existing_payment = await self.get_payment(payment_id)
            if not existing_payment:
                raise Exception("Payment not found")
            
            # Use direct DynamoDB update with explicit type handling to avoid decimal conversion issues
            update_expression = "SET #status = :status, #confirmed_at = :confirmed_at, #callback_received = :callback_received, #updated_at = :updated_at"
            
            expression_attribute_names = {
                '#status': 'status',
                '#confirmed_at': 'workday_confirmed_at', 
                '#callback_received': 'workday_callback_received',
                '#updated_at': 'updated_at'
            }
            
            expression_attribute_values = {
                ':status': status,  # String - no conversion needed
                ':confirmed_at': confirmed_at,  # String - no conversion needed  
                ':callback_received': True,  # Boolean - DynamoDB native type
                ':updated_at': datetime.utcnow().isoformat()  # String - pre-converted
            }
            
            logger.info(f"Workday callback update: {payment_id} -> status: {status}, confirmed_at: {confirmed_at}")
            
            response = self.payments_table.update_item(
                Key={'id': payment_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="ALL_NEW"
            )
            
            logger.info(f"Workday callback update successful for payment {payment_id}")
            
            # Convert the response carefully to avoid decimal conversion issues
            try:
                converted_result = self._convert_item_from_db(response['Attributes'])
                logger.info(f"Response conversion successful")
                return converted_result
            except Exception as convert_error:
                logger.error(f"Error converting response from DB: {convert_error}")
                import traceback
                logger.error(f"Conversion traceback: {traceback.format_exc()}")
                raise
            
        except ClientError as e:
            logger.error(f"Error in Workday callback update for payment {payment_id}: {e}")
            raise Exception(f"Failed to update payment via Workday callback: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Workday callback update for payment {payment_id}: {e}")
            raise Exception(f"Failed to update payment via Workday callback: {str(e)}")

    async def list_payments(self, status_filter: Optional[str] = None, vendor_id_filter: Optional[str] = None, invoice_id_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all payments with optional filters"""
        try:
            filter_expression = None
            filter_conditions = []
            
            if status_filter:
                filter_conditions.append(boto3.dynamodb.conditions.Attr('status').eq(status_filter))
            if vendor_id_filter:
                filter_conditions.append(boto3.dynamodb.conditions.Attr('vendor_id').eq(vendor_id_filter))
            if invoice_id_filter:
                filter_conditions.append(boto3.dynamodb.conditions.Attr('invoice_id').eq(invoice_id_filter))
            
            # Combine filter conditions
            if len(filter_conditions) == 1:
                filter_expression = filter_conditions[0]
            elif len(filter_conditions) > 1:
                filter_expression = filter_conditions[0]
                for condition in filter_conditions[1:]:
                    filter_expression = filter_expression & condition
            
            if filter_expression:
                response = self.payments_table.scan(FilterExpression=filter_expression)
            else:
                response = self.payments_table.scan()
            
            items = [self._convert_item_from_db(item) for item in response.get('Items', [])]
            
            logger.info(f"Retrieved {len(items)} payments")
            return items
            
        except ClientError as e:
            logger.error(f"Error listing payments: {e}")
            raise Exception(f"Failed to list payments: {str(e)}")

    async def approve_invoice_and_create_payment(self, invoice_id: str, approved_by: str) -> Dict[str, Any]:
        """Approve a reconciled invoice and create payment record"""
        try:
            # Get the invoice
            invoice = await self.get_invoice(invoice_id)
            if not invoice:
                raise Exception("Invoice not found")
            
            # Check if invoice is in reconciled/matched status
            if invoice.get('status') != 'matched':
                raise Exception(f"Cannot approve invoice with status '{invoice.get('status')}'. Invoice must be 'matched'.")
            
            # Get the purchase order to find the vendor_id
            po_id = invoice.get('po_id')
            if not po_id:
                raise Exception("Invoice is missing purchase order reference")
            
            purchase_order = await self.get_purchase_order(po_id)
            if not purchase_order:
                raise Exception("Associated purchase order not found")
            
            vendor_id = purchase_order.get('vendor_id')
            if not vendor_id:
                raise Exception("Purchase order is missing vendor reference")
            
            # Don't change invoice status - keep it as 'matched'
            # Just update with approval metadata
            await self.update_invoice(invoice_id, {
                'approved_by': approved_by,
                'approved_at': datetime.utcnow()
            })
            
            # Create payment record
            payment_data = {
                'invoice_id': invoice_id,
                'vendor_id': vendor_id,
                'amount': float(invoice.get('total_amount', 0)),
                'currency': 'USD',
                'status': 'approved',
                'approved_at': datetime.utcnow()
            }
            
            payment = await self.create_payment(payment_data)
            
            # Log the approval action
            await self.create_audit_log(
                action="APPROVE",
                entity_type="Invoice",
                entity_id=invoice_id,
                details={
                    "approved_by": approved_by,
                    "payment_id": payment.get('id'),
                    "amount": payment_data['amount'],
                    "currency": payment_data['currency'],
                    "status": payment_data['status']
                },
                log_type="PAYMENT_ACTION"
            )
            
            logger.info(f"Approved invoice {invoice_id} and created payment {payment.get('id')}")
            return payment
            
        except ClientError as e:
            logger.error(f"Error approving invoice {invoice_id}: {e}")
            raise Exception(f"Failed to approve invoice: {str(e)}")

# Global service instance
db_service = DynamoDBService() 