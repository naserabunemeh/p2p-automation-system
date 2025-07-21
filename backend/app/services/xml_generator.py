from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import json

class XMLGenerator:
    """Service for generating XML files for payments and other P2P entities"""
    
    @staticmethod
    def generate_payment_xml(payment_data: Dict[str, Any]) -> str:
        """
        Generate Workday-compatible XML for payment data
        
        Args:
            payment_data: Dictionary containing payment information
            
        Returns:
            Formatted XML string matching Workday schema
        """
        # Create root element - exact Workday format
        root = ET.Element("Payment")
        
        # Add required elements in exact order per Workday schema
        ET.SubElement(root, "ID").text = str(payment_data.get("id", ""))
        ET.SubElement(root, "InvoiceID").text = str(payment_data.get("invoice_id", ""))
        ET.SubElement(root, "VendorID").text = str(payment_data.get("vendor_id", ""))
        ET.SubElement(root, "Amount").text = f"{payment_data.get('amount', 0.00):.2f}"
        ET.SubElement(root, "Currency").text = str(payment_data.get("currency", "USD"))
        ET.SubElement(root, "Status").text = str(payment_data.get("status", "approved"))
        ET.SubElement(root, "Timestamp").text = XMLGenerator._format_datetime(payment_data.get("approved_at"))
        
        # Format XML with proper indentation
        return XMLGenerator._prettify_xml(root)
    
    @staticmethod
    def generate_payment_json(payment_data: Dict[str, Any]) -> str:
        """
        Generate JSON mirror of Workday-compatible XML payment data
        
        Args:
            payment_data: Dictionary containing payment information
            
        Returns:
            JSON string matching XML structure
        """
        # Create JSON structure that mirrors the XML
        json_structure = {
            "Payment": {
                "ID": str(payment_data.get("id", "")),
                "InvoiceID": str(payment_data.get("invoice_id", "")),
                "VendorID": str(payment_data.get("vendor_id", "")),
                "Amount": f"{payment_data.get('amount', 0.00):.2f}",
                "Currency": str(payment_data.get("currency", "USD")),
                "Status": str(payment_data.get("status", "approved")),
                "Timestamp": XMLGenerator._format_datetime(payment_data.get("approved_at"))
            }
        }
        
        return json.dumps(json_structure, indent=2, ensure_ascii=False)
    
    @staticmethod
    def generate_vendor_xml(vendor_data: Dict[str, Any]) -> str:
        """
        Generate XML for vendor data
        
        Args:
            vendor_data: Dictionary containing vendor information
            
        Returns:
            Formatted XML string
        """
        root = ET.Element("vendor")
        root.set("xmlns", "http://www.workday.com/vendors")
        root.set("version", "1.0")
        
        # Vendor header
        header = ET.SubElement(root, "vendor_header")
        ET.SubElement(header, "vendor_id").text = str(vendor_data.get("id", ""))
        ET.SubElement(header, "vendor_name").text = str(vendor_data.get("name", ""))
        ET.SubElement(header, "status").text = str(vendor_data.get("status", ""))
        ET.SubElement(header, "created_date").text = XMLGenerator._format_datetime(vendor_data.get("created_at"))
        
        # Contact information
        contact = ET.SubElement(root, "contact_info")
        ET.SubElement(contact, "email").text = str(vendor_data.get("email", ""))
        ET.SubElement(contact, "phone").text = str(vendor_data.get("phone", ""))
        ET.SubElement(contact, "address").text = str(vendor_data.get("address", ""))
        
        # Financial information
        financial = ET.SubElement(root, "financial_info")
        ET.SubElement(financial, "tax_id").text = str(vendor_data.get("tax_id", ""))
        ET.SubElement(financial, "payment_terms").text = str(vendor_data.get("payment_terms", ""))
        
        return XMLGenerator._prettify_xml(root)
    
    @staticmethod
    def generate_purchase_order_xml(po_data: Dict[str, Any]) -> str:
        """
        Generate XML for purchase order data
        
        Args:
            po_data: Dictionary containing purchase order information
            
        Returns:
            Formatted XML string
        """
        root = ET.Element("purchase_order")
        root.set("xmlns", "http://www.workday.com/purchase_orders")
        root.set("version", "1.0")
        
        # PO header
        header = ET.SubElement(root, "po_header")
        ET.SubElement(header, "po_id").text = str(po_data.get("id", ""))
        ET.SubElement(header, "po_number").text = str(po_data.get("po_number", ""))
        ET.SubElement(header, "vendor_id").text = str(po_data.get("vendor_id", ""))
        ET.SubElement(header, "status").text = str(po_data.get("status", ""))
        ET.SubElement(header, "total_amount").text = str(po_data.get("total_amount", "0.00"))
        ET.SubElement(header, "created_date").text = XMLGenerator._format_datetime(po_data.get("created_at"))
        
        # Requestor information
        requestor = ET.SubElement(root, "requestor_info")
        ET.SubElement(requestor, "requested_by").text = str(po_data.get("requested_by", ""))
        ET.SubElement(requestor, "approved_by").text = str(po_data.get("approved_by", ""))
        
        # Line items
        line_items = ET.SubElement(root, "line_items")
        for item in po_data.get("line_items", []):
            line_item = ET.SubElement(line_items, "line_item")
            ET.SubElement(line_item, "line_number").text = str(item.get("line_number", ""))
            ET.SubElement(line_item, "description").text = str(item.get("description", ""))
            ET.SubElement(line_item, "quantity").text = str(item.get("quantity", ""))
            ET.SubElement(line_item, "unit_price").text = str(item.get("unit_price", ""))
            ET.SubElement(line_item, "total_amount").text = str(item.get("total_amount", ""))
        
        # Delivery information
        if po_data.get("delivery_date"):
            delivery = ET.SubElement(root, "delivery_info")
            ET.SubElement(delivery, "delivery_date").text = XMLGenerator._format_datetime(po_data.get("delivery_date"))
        
        return XMLGenerator._prettify_xml(root)
    
    @staticmethod
    def generate_invoice_xml(invoice_data: Dict[str, Any]) -> str:
        """
        Generate XML for invoice data
        
        Args:
            invoice_data: Dictionary containing invoice information
            
        Returns:
            Formatted XML string
        """
        root = ET.Element("invoice")
        root.set("xmlns", "http://www.workday.com/invoices")
        root.set("version", "1.0")
        
        # Invoice header
        header = ET.SubElement(root, "invoice_header")
        ET.SubElement(header, "invoice_id").text = str(invoice_data.get("id", ""))
        ET.SubElement(header, "invoice_number").text = str(invoice_data.get("invoice_number", ""))
        ET.SubElement(header, "vendor_id").text = str(invoice_data.get("vendor_id", ""))
        ET.SubElement(header, "po_id").text = str(invoice_data.get("po_id", ""))
        ET.SubElement(header, "status").text = str(invoice_data.get("status", ""))
        
        # Dates
        dates = ET.SubElement(root, "dates")
        ET.SubElement(dates, "invoice_date").text = XMLGenerator._format_datetime(invoice_data.get("invoice_date"))
        ET.SubElement(dates, "due_date").text = XMLGenerator._format_datetime(invoice_data.get("due_date"))
        ET.SubElement(dates, "created_date").text = XMLGenerator._format_datetime(invoice_data.get("created_at"))
        
        # Financial details
        financial = ET.SubElement(root, "financial_details")
        ET.SubElement(financial, "subtotal").text = str(invoice_data.get("subtotal", "0.00"))
        ET.SubElement(financial, "tax_amount").text = str(invoice_data.get("tax_amount", "0.00"))
        ET.SubElement(financial, "total_amount").text = str(invoice_data.get("total_amount", "0.00"))
        
        # Line items
        line_items = ET.SubElement(root, "line_items")
        for item in invoice_data.get("line_items", []):
            line_item = ET.SubElement(line_items, "line_item")
            ET.SubElement(line_item, "line_number").text = str(item.get("line_number", ""))
            ET.SubElement(line_item, "po_line_reference").text = str(item.get("po_line_reference", ""))
            ET.SubElement(line_item, "description").text = str(item.get("description", ""))
            ET.SubElement(line_item, "quantity").text = str(item.get("quantity", ""))
            ET.SubElement(line_item, "unit_price").text = str(item.get("unit_price", ""))
            ET.SubElement(line_item, "total_amount").text = str(item.get("total_amount", ""))
        
        # Approval information
        if invoice_data.get("approved_by"):
            approval = ET.SubElement(root, "approval_info")
            ET.SubElement(approval, "approved_by").text = str(invoice_data.get("approved_by"))
            ET.SubElement(approval, "approval_date").text = XMLGenerator._format_datetime(invoice_data.get("updated_at"))
        
        # Notes
        if invoice_data.get("notes"):
            ET.SubElement(root, "notes").text = str(invoice_data.get("notes"))
        
        return XMLGenerator._prettify_xml(root)
    
    @staticmethod
    def _format_datetime(dt: Any) -> str:
        """Format datetime for XML output"""
        if dt is None:
            return ""
        if isinstance(dt, str):
            return dt
        if isinstance(dt, datetime):
            return dt.isoformat()
        return str(dt)
    
    @staticmethod
    def _prettify_xml(root: ET.Element) -> str:
        """Return a pretty-printed XML string for the Element"""
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding=None)

class XMLValidator:
    """Service for validating XML files against schemas"""
    
    @staticmethod
    def validate_payment_xml(xml_content: str) -> tuple[bool, str]:
        """
        Validate payment XML content
        
        Args:
            xml_content: XML string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            root = ET.fromstring(xml_content)
            
            # Basic validation checks
            if root.tag != "payment":
                return False, "Root element must be 'payment'"
            
            # Check required elements
            required_elements = ["payment_header", "vendor", "invoice", "payment_details"]
            for element in required_elements:
                if root.find(element) is None:
                    return False, f"Missing required element: {element}"
            
            # Check payment header required fields
            header = root.find("payment_header")
            required_header_fields = ["payment_id", "payment_date", "status"]
            for field in required_header_fields:
                if header.find(field) is None:
                    return False, f"Missing required header field: {field}"
            
            return True, "XML is valid"
            
        except ET.ParseError as e:
            return False, f"XML parsing error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}" 