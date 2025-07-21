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

# Global service instance
db_service = DynamoDBService() 