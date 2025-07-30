"""
XML Generation Service for ERP-Lite P2P Automation System

This module provides comprehensive XML generation capabilities for the P2P automation
system, focusing on Workday-compatible formats for payments and other business entities.
It includes both XML and JSON generation for flexible integration options.

Key Features:
    - Workday-compatible XML format generation
    - JSON mirror format for modern integrations
    - Proper XML formatting with indentation
    - Comprehensive validation services
    - Support for all major P2P entities

Business Entity Support:
    - Payment records with full audit trail
    - Vendor information with contact details
    - Purchase orders with line item details
    - Invoice records with approval workflow

Standards Compliance:
    - XML schema validation
    - ISO datetime formatting
    - Proper encoding and character handling
    - Structured error reporting

Author: Development Team
Version: 1.0.0
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import json

class XMLGenerator:
    """
    Service class for generating XML files for payments and other P2P entities.
    
    This class provides static methods for converting Python dictionaries into
    properly formatted XML that complies with Workday schema requirements.
    It supports multiple entity types and provides both XML and JSON outputs.
    """
    
    @staticmethod
    def generate_payment_xml(payment_data: Dict[str, Any]) -> str:
        """
        Generate Workday-compatible XML for payment data.
        
        This method creates XML that follows Workday's payment schema requirements,
        ensuring proper element ordering and data formatting for seamless integration.
        
        Args:
            payment_data (Dict[str, Any]): Dictionary containing payment information with keys:
                - id: Payment unique identifier
                - invoice_id: Associated invoice identifier
                - vendor_id: Vendor reference
                - amount: Payment amount (will be formatted to 2 decimal places)
                - currency: Currency code (defaults to USD)
                - status: Payment status (approved, sent, failed)
                - approved_at: Approval timestamp
                
        Returns:
            str: Formatted XML string matching Workday payment schema with proper indentation
            
        Example:
            >>> payment_data = {
            ...     "id": "pay_123",
            ...     "invoice_id": "inv_456",
            ...     "vendor_id": "vendor_789",
            ...     "amount": 1500.50,
            ...     "currency": "USD",
            ...     "status": "approved",
            ...     "approved_at": datetime.now()
            ... }
            >>> xml_content = XMLGenerator.generate_payment_xml(payment_data)
        """
        # Create root payment element - follows Workday schema structure
        root = ET.Element("Payment")
        
        # Add required payment elements in Workday-specified order
        # Element order is critical for Workday schema validation
        ET.SubElement(root, "ID").text = str(payment_data.get("id", ""))
        ET.SubElement(root, "InvoiceID").text = str(payment_data.get("invoice_id", ""))
        ET.SubElement(root, "VendorID").text = str(payment_data.get("vendor_id", ""))
        
        # Format amount to exactly 2 decimal places as required by financial systems
        ET.SubElement(root, "Amount").text = f"{payment_data.get('amount', 0.00):.2f}"
        ET.SubElement(root, "Currency").text = str(payment_data.get("currency", "USD"))
        ET.SubElement(root, "Status").text = str(payment_data.get("status", "approved"))
        
        # Format timestamp in ISO format for consistent datetime handling
        ET.SubElement(root, "Timestamp").text = XMLGenerator._format_datetime(payment_data.get("approved_at"))
        
        # Return properly formatted XML with consistent indentation
        return XMLGenerator._prettify_xml(root)
    
    @staticmethod
    def generate_payment_json(payment_data: Dict[str, Any]) -> str:
        """
        Generate JSON mirror of Workday-compatible XML payment data.
        
        This method creates a JSON representation that maintains the same structure
        as the XML format, enabling modern API integrations while preserving
        compatibility with XML-based systems.
        
        Args:
            payment_data (Dict[str, Any]): Dictionary containing payment information
                (same structure as generate_payment_xml)
                
        Returns:
            str: JSON string with proper formatting and indentation that mirrors
                 the XML structure for consistent data representation
                 
        Example:
            >>> json_content = XMLGenerator.generate_payment_json(payment_data)
            >>> # Returns formatted JSON with Payment root object
        """
        # Create JSON structure that mirrors the XML hierarchy
        # This ensures consistency between XML and JSON representations
        json_structure = {
            "Payment": {
                "ID": str(payment_data.get("id", "")),
                "InvoiceID": str(payment_data.get("invoice_id", "")),
                "VendorID": str(payment_data.get("vendor_id", "")),
                # Maintain same decimal formatting as XML for consistency
                "Amount": f"{payment_data.get('amount', 0.00):.2f}",
                "Currency": str(payment_data.get("currency", "USD")),
                "Status": str(payment_data.get("status", "approved")),
                "Timestamp": XMLGenerator._format_datetime(payment_data.get("approved_at"))
            }
        }
        
        # Return formatted JSON with proper indentation and UTF-8 support
        return json.dumps(json_structure, indent=2, ensure_ascii=False)
    
    @staticmethod
    def generate_vendor_xml(vendor_data: Dict[str, Any]) -> str:
        """
        Generate XML for vendor data following enterprise standards.
        
        Creates comprehensive vendor XML with proper namespace declarations
        and structured information sections for contact, financial, and audit data.
        
        Args:
            vendor_data (Dict[str, Any]): Dictionary containing vendor information including:
                - id, name, status: Basic vendor identifiers
                - email, phone, address: Contact information
                - tax_id, payment_terms: Financial details
                - created_at: Audit timestamp
                
        Returns:
            str: Formatted XML string with vendor information organized in logical sections
        """
        # Create root vendor element with appropriate namespace for enterprise systems
        root = ET.Element("vendor")
        root.set("xmlns", "http://www.workday.com/vendors")  # Workday namespace
        root.set("version", "1.0")  # Schema version for compatibility
        
        # Vendor header section - core identification information
        header = ET.SubElement(root, "vendor_header")
        ET.SubElement(header, "vendor_id").text = str(vendor_data.get("id", ""))
        ET.SubElement(header, "vendor_name").text = str(vendor_data.get("name", ""))
        ET.SubElement(header, "status").text = str(vendor_data.get("status", ""))
        ET.SubElement(header, "created_date").text = XMLGenerator._format_datetime(vendor_data.get("created_at"))
        
        # Contact information section - communication details
        contact = ET.SubElement(root, "contact_info")
        ET.SubElement(contact, "email").text = str(vendor_data.get("email", ""))
        ET.SubElement(contact, "phone").text = str(vendor_data.get("phone", ""))
        ET.SubElement(contact, "address").text = str(vendor_data.get("address", ""))
        
        # Financial information section - payment and tax details
        financial = ET.SubElement(root, "financial_info")
        ET.SubElement(financial, "tax_id").text = str(vendor_data.get("tax_id", ""))
        ET.SubElement(financial, "payment_terms").text = str(vendor_data.get("payment_terms", ""))
        
        return XMLGenerator._prettify_xml(root)
    
    @staticmethod
    def generate_purchase_order_xml(po_data: Dict[str, Any]) -> str:
        """
        Generate XML for purchase order data with comprehensive structure.
        
        Creates detailed purchase order XML including header information,
        line items, requestor details, and delivery information following
        enterprise procurement standards.
        
        Args:
            po_data (Dict[str, Any]): Dictionary containing purchase order data including:
                - Basic PO information (id, po_number, vendor_id, status, total_amount)
                - Requestor information (requested_by, approved_by)
                - Line items array with detailed item information
                - Optional delivery information
                
        Returns:
            str: Comprehensive XML structure for purchase order processing
        """
        # Create root purchase order element with enterprise namespace
        root = ET.Element("purchase_order")
        root.set("xmlns", "http://www.workday.com/purchase_orders")
        root.set("version", "1.0")
        
        # PO header section - essential purchase order metadata
        header = ET.SubElement(root, "po_header")
        ET.SubElement(header, "po_id").text = str(po_data.get("id", ""))
        ET.SubElement(header, "po_number").text = str(po_data.get("po_number", ""))
        ET.SubElement(header, "vendor_id").text = str(po_data.get("vendor_id", ""))
        ET.SubElement(header, "status").text = str(po_data.get("status", ""))
        ET.SubElement(header, "total_amount").text = str(po_data.get("total_amount", "0.00"))
        ET.SubElement(header, "created_date").text = XMLGenerator._format_datetime(po_data.get("created_at"))
        
        # Requestor information section - approval workflow details
        requestor = ET.SubElement(root, "requestor_info")
        ET.SubElement(requestor, "requested_by").text = str(po_data.get("requested_by", ""))
        ET.SubElement(requestor, "approved_by").text = str(po_data.get("approved_by", ""))
        
        # Line items section - detailed item information
        line_items = ET.SubElement(root, "line_items")
        for item in po_data.get("line_items", []):
            line_item = ET.SubElement(line_items, "line_item")
            # Add comprehensive item details for each line
            ET.SubElement(line_item, "line_number").text = str(item.get("line_number", ""))
            ET.SubElement(line_item, "description").text = str(item.get("description", ""))
            ET.SubElement(line_item, "quantity").text = str(item.get("quantity", ""))
            ET.SubElement(line_item, "unit_price").text = str(item.get("unit_price", ""))
            ET.SubElement(line_item, "total_amount").text = str(item.get("total_amount", ""))
        
        # Optional delivery information section - logistics details
        if po_data.get("delivery_date"):
            delivery = ET.SubElement(root, "delivery_info")
            ET.SubElement(delivery, "delivery_date").text = XMLGenerator._format_datetime(po_data.get("delivery_date"))
        
        return XMLGenerator._prettify_xml(root)
    
    @staticmethod
    def generate_invoice_xml(invoice_data: Dict[str, Any]) -> str:
        """
        Generate XML for invoice data with complete billing structure.
        
        Creates comprehensive invoice XML including header, financial details,
        line items, approval information, and notes following accounts payable
        processing standards.
        
        Args:
            invoice_data (Dict[str, Any]): Dictionary containing invoice information including:
                - Header data (id, invoice_number, vendor_id, po_id, status)
                - Date information (invoice_date, due_date, created_at)
                - Financial details (subtotal, tax_amount, total_amount)
                - Line items with detailed billing information
                - Approval workflow data (approved_by, updated_at)
                - Optional notes
                
        Returns:
            str: Complete XML structure for invoice processing and approval workflows
        """
        # Create root invoice element with enterprise namespace
        root = ET.Element("invoice")
        root.set("xmlns", "http://www.workday.com/invoices")
        root.set("version", "1.0")
        
        # Invoice header section - core invoice identification
        header = ET.SubElement(root, "invoice_header")
        ET.SubElement(header, "invoice_id").text = str(invoice_data.get("id", ""))
        ET.SubElement(header, "invoice_number").text = str(invoice_data.get("invoice_number", ""))
        ET.SubElement(header, "vendor_id").text = str(invoice_data.get("vendor_id", ""))
        ET.SubElement(header, "po_id").text = str(invoice_data.get("po_id", ""))
        ET.SubElement(header, "status").text = str(invoice_data.get("status", ""))
        
        # Dates section - critical timing information for payment processing
        dates = ET.SubElement(root, "dates")
        ET.SubElement(dates, "invoice_date").text = XMLGenerator._format_datetime(invoice_data.get("invoice_date"))
        ET.SubElement(dates, "due_date").text = XMLGenerator._format_datetime(invoice_data.get("due_date"))
        ET.SubElement(dates, "created_date").text = XMLGenerator._format_datetime(invoice_data.get("created_at"))
        
        # Financial details section - monetary information for accounting
        financial = ET.SubElement(root, "financial_details")
        ET.SubElement(financial, "subtotal").text = str(invoice_data.get("subtotal", "0.00"))
        ET.SubElement(financial, "tax_amount").text = str(invoice_data.get("tax_amount", "0.00"))
        ET.SubElement(financial, "total_amount").text = str(invoice_data.get("total_amount", "0.00"))
        
        # Line items section - detailed billing breakdown
        line_items = ET.SubElement(root, "line_items")
        for item in invoice_data.get("line_items", []):
            line_item = ET.SubElement(line_items, "line_item")
            # Comprehensive line item details for audit and matching
            ET.SubElement(line_item, "line_number").text = str(item.get("line_number", ""))
            ET.SubElement(line_item, "po_line_reference").text = str(item.get("po_line_reference", ""))
            ET.SubElement(line_item, "description").text = str(item.get("description", ""))
            ET.SubElement(line_item, "quantity").text = str(item.get("quantity", ""))
            ET.SubElement(line_item, "unit_price").text = str(item.get("unit_price", ""))
            ET.SubElement(line_item, "total_amount").text = str(item.get("total_amount", ""))
        
        # Approval information section - workflow and audit trail
        if invoice_data.get("approved_by"):
            approval = ET.SubElement(root, "approval_info")
            ET.SubElement(approval, "approved_by").text = str(invoice_data.get("approved_by"))
            ET.SubElement(approval, "approval_date").text = XMLGenerator._format_datetime(invoice_data.get("updated_at"))
        
        # Optional notes section - additional context and comments
        if invoice_data.get("notes"):
            ET.SubElement(root, "notes").text = str(invoice_data.get("notes"))
        
        return XMLGenerator._prettify_xml(root)
    
    @staticmethod
    def _format_datetime(dt: Any) -> str:
        """
        Format datetime objects for consistent XML output.
        
        This method ensures all datetime values are properly formatted for XML
        consumption, handling various input types and providing consistent
        ISO format output.
        
        Args:
            dt (Any): Datetime object, string, or None value to format
            
        Returns:
            str: ISO formatted datetime string or empty string if None
        """
        if dt is None:
            return ""
        if isinstance(dt, str):
            return dt  # Already formatted string
        if isinstance(dt, datetime):
            return dt.isoformat()  # ISO format for XML standards
        return str(dt)  # Fallback to string conversion
    
    @staticmethod
    def _prettify_xml(root: ET.Element) -> str:
        """
        Return a pretty-printed XML string for the Element with proper formatting.
        
        This method takes an XML Element and returns a nicely formatted string
        with proper indentation and line breaks for human readability and
        consistent formatting across all generated XML.
        
        Args:
            root (ET.Element): Root XML element to format
            
        Returns:
            str: Formatted XML string with proper indentation and structure
        """
        # Convert to string and re-parse for proper formatting
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        
        # Return with consistent 2-space indentation and UTF-8 encoding
        return reparsed.toprettyxml(indent="  ", encoding=None)

class XMLValidator:
    """
    Service class for validating XML files against business schemas.
    
    This class provides validation services to ensure generated XML meets
    the required schema standards and contains all necessary elements for
    successful processing by downstream systems.
    """
    
    @staticmethod
    def validate_payment_xml(xml_content: str) -> tuple[bool, str]:
        """
        Validate payment XML content against expected schema requirements.
        
        This method performs comprehensive validation of payment XML to ensure
        it contains all required elements and follows the expected structure
        for successful processing by payment systems.
        
        Args:
            xml_content (str): XML string content to validate
            
        Returns:
            tuple[bool, str]: Validation result as (is_valid, error_message)
                - is_valid: True if XML passes all validation checks
                - error_message: Descriptive error message if validation fails,
                  or success message if validation passes
                  
        Validation Checks:
            - Valid XML parsing
            - Correct root element name
            - Required element presence
            - Required header field validation
            
        Example:
            >>> is_valid, message = XMLValidator.validate_payment_xml(xml_string)
            >>> if not is_valid:
            ...     print(f"Validation failed: {message}")
        """
        try:
            # Parse XML content and validate structure
            root = ET.fromstring(xml_content)
            
            # Validate root element - must be 'payment' for payment XML
            if root.tag != "payment":
                return False, "Root element must be 'payment'"
            
            # Check for required top-level elements in payment structure
            required_elements = ["payment_header", "vendor", "invoice", "payment_details"]
            for element in required_elements:
                if root.find(element) is None:
                    return False, f"Missing required element: {element}"
            
            # Validate payment header contains required fields for processing
            header = root.find("payment_header")
            required_header_fields = ["payment_id", "payment_date", "status"]
            for field in required_header_fields:
                if header.find(field) is None:
                    return False, f"Missing required header field: {field}"
            
            # All validation checks passed successfully
            return True, "XML is valid"
            
        except ET.ParseError as e:
            # Handle XML parsing errors with descriptive messages
            return False, f"XML parsing error: {str(e)}"
        except Exception as e:
            # Handle any other validation errors
            return False, f"Validation error: {str(e)}" 