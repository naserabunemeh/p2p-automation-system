#!/usr/bin/env python3
"""
Complete P2P Automation System Demo Script
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def make_request(method, endpoint, data=None):
    """Make HTTP request and return response"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    try:
        if method == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers)
        elif method == "GET":
            response = requests.get(url)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        print(f"🌐 {method} {endpoint}")
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code >= 400:
            print(f"❌ Error: {response.text}")
            return None
        
        result = response.json()
        print(f"✅ Response: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return None

def test_workday_callback():
    """Test the Workday callback directly"""
    print("\n🧪 Testing Workday callback directly...")
    
    # Use a known payment ID from previous run
    payment_id = "6a049baf-9a06-4c26-89c0-7979bef092c3"
    
    callback_data = {
        "payment_id": payment_id,
        "status": "sent"
    }
    callback_response = make_request("POST", "/api/v1/workday/callback", callback_data)
    
    if callback_response and callback_response.get("success"):
        print("✅ Workday callback test successful!")
        
        # Check status after callback
        status_response = make_request("GET", f"/api/v1/workday/status/{payment_id}")
        if status_response and status_response.get("success"):
            integration_status = status_response["data"]["integration_status"]
            print(f"✅ Integration status after callback: {integration_status}")
    else:
        print("❌ Workday callback test failed")

def main():
    print("🚀 Starting P2P Automation Demo...")
    print("=" * 50)
    
    # First, test the Workday callback to see if it's fixed
    test_workday_callback()
    
    # Continue with full demo...
    
    # Step 1: Health Check
    print("\n📋 Step 1: Health Check")
    health = make_request("GET", "/health")
    if not health:
        print("❌ Server not responding!")
        return
    
    # Step 2: Create Vendor
    print("\n📋 Step 2: Creating vendor...")
    vendor_data = {
        "name": "ACME Supplies Corp",
        "email": "accounting@acmesupplies.com",
        "phone": "+1-555-123-4567",
        "address": "123 Business Ave, Cityville, ST 12345",
        "tax_id": "12-3456789",
        "payment_terms": "Net 30"
    }
    vendor_response = make_request("POST", "/api/v1/vendors/", vendor_data)
    if not vendor_response or not vendor_response.get("success"):
        print("❌ Failed to create vendor!")
        return
    
    vendor_id = vendor_response["data"]["id"]
    print(f"✅ Vendor created with ID: {vendor_id}")
    
    # Step 3: Create Purchase Order
    print("\n📋 Step 3: Creating purchase order...")
    po_data = {
        "vendor_id": vendor_id,
        "items": [
            {
                "description": "Office Supplies - Pens",
                "quantity": 100,
                "unit_price": 2.50,
                "total_amount": 250.00
            },
            {
                "description": "Office Supplies - Paper",
                "quantity": 50,
                "unit_price": 12.00,
                "total_amount": 600.00
            }
        ],
        "total_amount": 850.00
    }
    po_response = make_request("POST", "/api/v1/purchase-orders/", po_data)
    if not po_response or not po_response.get("success"):
        print("❌ Failed to create purchase order!")
        return
    
    po_id = po_response["data"]["id"]
    print(f"✅ Purchase Order created with ID: {po_id}")
    
    # Step 4: Approve Purchase Order
    print("\n📋 Step 4: Approving purchase order...")
    approve_response = make_request("PUT", f"/api/v1/purchase-orders/{po_id}/approve")
    if not approve_response or not approve_response.get("success"):
        print("❌ Failed to approve purchase order!")
        return
    
    print("✅ Purchase Order approved")
    
    # Step 5: Submit Invoice
    print("\n📋 Step 5: Submitting invoice...")
    invoice_data = {
        "po_id": po_id,
        "invoice_number": f"INV-2025-{int(time.time())}",
        "items": [
            {
                "description": "Office Supplies - Pens",
                "quantity": 100,
                "unit_price": 2.50
            },
            {
                "description": "Office Supplies - Paper", 
                "quantity": 50,
                "unit_price": 12.00
            }
        ],
        "total_amount": 850.00
    }
    invoice_response = make_request("POST", "/api/v1/invoices/", invoice_data)
    if not invoice_response or not invoice_response.get("success"):
        print("❌ Failed to create invoice!")
        return
    
    invoice_id = invoice_response["data"]["id"]
    print(f"✅ Invoice created with ID: {invoice_id}")
    
    # Step 6: Reconcile Invoice
    print("\n📋 Step 6: Reconciling invoice...")
    reconcile_response = make_request("PUT", f"/api/v1/invoices/{invoice_id}/reconcile")
    if not reconcile_response or not reconcile_response.get("success"):
        print("❌ Failed to reconcile invoice!")
        return
    
    print("✅ Invoice reconciled")
    
    # Step 7: Approve Payment
    print("\n📋 Step 7: Approving payment...")
    payment_data = {
        "approved_by": "manager@company.com"
    }
    payment_response = make_request("POST", f"/api/v1/payments/{invoice_id}/approve", payment_data)
    if not payment_response or not payment_response.get("success"):
        print("❌ Failed to approve payment!")
        return
    
    payment_id = payment_response["data"]["payment"]["id"]
    print(f"✅ Payment approved with ID: {payment_id}")
    
    # Step 8: Workday Callback
    print("\n📋 Step 8: Simulating Workday callback...")
    callback_data = {
        "payment_id": payment_id,
        "status": "sent"
    }
    callback_response = make_request("POST", "/api/v1/workday/callback", callback_data)
    if callback_response and callback_response.get("success"):
        print("✅ Workday callback completed successfully!")
    else:
        print("⚠️  Workday callback had issues but continuing...")
    
    # Step 9: Verify Status
    print("\n📋 Step 9: Verifying integration status...")
    status_response = make_request("GET", f"/api/v1/workday/status/{payment_id}")
    if status_response and status_response.get("success"):
        integration_status = status_response["data"]["integration_status"]
        print(f"✅ Integration status: {integration_status}")
    
    # Step 10: Check exports
    print("\n📋 Step 10: Checking exports...")
    exports_response = make_request("GET", "/api/v1/exports/")
    if exports_response and exports_response.get("success"):
        exports = exports_response["data"]["items"]
        xml_files = [f for f in exports if f.get("file_type") == "xml"]
        json_files = [f for f in exports if f.get("file_type") == "json"]
        print(f"✅ Found {len(xml_files)} XML and {len(json_files)} JSON export files")
    
    print("\n" + "=" * 50)
    print("🎉 P2P Automation Demo completed successfully!")
    print(f"📊 Results Summary:")
    print(f"  • Vendor ID: {vendor_id}")
    print(f"  • Purchase Order ID: {po_id}")
    print(f"  • Invoice ID: {invoice_id}")
    print(f"  • Payment ID: {payment_id}")
    print(f"📁 Check results at: http://localhost:8000/docs")

if __name__ == "__main__":
    main() 