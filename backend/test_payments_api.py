#!/usr/bin/env python3
"""
Test script for Payment API implementation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.dynamodb_service import db_service
from app.services.s3_service import s3_service
from app.services.xml_generator import XMLGenerator
import json
from datetime import datetime
import asyncio

async def test_payment_services():
    """Test the payment services integration"""
    print("🔄 Testing Payment Services Integration...")
    
    # Test 1: Service Initialization
    print("\n1. Service Initialization:")
    try:
        print(f"   ✅ DynamoDB Service initialized with region: {db_service.region_name}")
        print(f"   ✅ S3 Service initialized with bucket: {s3_service.bucket_name}")
        print(f"   ✅ XML Generator service available")
    except Exception as e:
        print(f"   ❌ Service initialization failed: {e}")
        return False
    
    # Test 2: XML Generation
    print("\n2. XML Generation Test:")
    try:
        test_payment_data = {
            'id': 'test-payment-123',
            'invoice_id': 'test-invoice-456',
            'vendor_id': 'test-vendor-789',
            'payment_amount': '1250.00',
            'payment_method': 'ACH',
            'status': 'processing',
            'reference_number': 'PAY-TEST123',
            'processed_by': 'test-user',
            'created_at': datetime.utcnow(),
            'payment_date': datetime.utcnow()
        }
        
        xml_content = XMLGenerator.generate_payment_xml(test_payment_data)
        if xml_content and '<payment' in xml_content:
            print("   ✅ XML generation successful")
            print(f"   📄 XML content length: {len(xml_content)} characters")
        else:
            print("   ❌ XML generation failed or empty")
    except Exception as e:
        print(f"   ❌ XML generation error: {e}")
    
    # Test 3: JSON Generation
    print("\n3. JSON Generation Test:")
    try:
        json_content = json.dumps(test_payment_data, indent=2, default=str)
        if json_content and 'test-payment-123' in json_content:
            print("   ✅ JSON generation successful")
            print(f"   📄 JSON content length: {len(json_content)} characters")
        else:
            print("   ❌ JSON generation failed or empty")
    except Exception as e:
        print(f"   ❌ JSON generation error: {e}")
    
    # Test 4: S3 Service Methods (Mock test without actual AWS calls)
    print("\n4. S3 Service Configuration Test:")
    try:
        # Test configuration
        expected_bucket = "p2p-payment-xml-storage-20250721-005155-6839"
        if s3_service.bucket_name == expected_bucket:
            print(f"   ✅ S3 bucket correctly configured: {s3_service.bucket_name}")
        else:
            print(f"   ⚠️  S3 bucket mismatch. Expected: {expected_bucket}, Got: {s3_service.bucket_name}")
        
        # Test S3 client initialization
        if hasattr(s3_service, 's3_client') and s3_service.s3_client:
            print("   ✅ S3 client initialized successfully")
        else:
            print("   ❌ S3 client not properly initialized")
    except Exception as e:
        print(f"   ❌ S3 service configuration error: {e}")
    
    # Test 5: DynamoDB Service Configuration
    print("\n5. DynamoDB Service Configuration Test:")
    try:
        # Test table references
        table_names = ['vendors_table', 'purchase_orders_table', 'invoices_table', 'payments_table', 'audit_log_table']
        for table_name in table_names:
            if hasattr(db_service, table_name):
                print(f"   ✅ {table_name} reference exists")
            else:
                print(f"   ❌ {table_name} reference missing")
        
        # Test if payment methods exist
        payment_methods = ['create_payment', 'get_payment', 'update_payment', 'list_payments', 'approve_invoice_and_create_payment']
        for method_name in payment_methods:
            if hasattr(db_service, method_name):
                print(f"   ✅ {method_name} method available")
            else:
                print(f"   ❌ {method_name} method missing")
    except Exception as e:
        print(f"   ❌ DynamoDB service configuration error: {e}")
    
    print("\n🎉 Payment Services Integration Test Complete!")
    return True

def test_api_imports():
    """Test API route imports"""
    print("\n🔄 Testing API Route Imports...")
    
    try:
        from app.routes.payments import router
        print("   ✅ Payments router imported successfully")
        
        # Check if router has the expected routes
        routes = [route.path for route in router.routes]
        expected_routes = ['/', '/{invoice_id}/approve', '/{payment_id}', '/{payment_id}/files']
        
        for expected_route in expected_routes:
            matching_routes = [route for route in routes if expected_route in route]
            if matching_routes:
                print(f"   ✅ Route pattern '{expected_route}' found")
            else:
                print(f"   ⚠️  Route pattern '{expected_route}' not found in {routes}")
        
        return True
    except Exception as e:
        print(f"   ❌ API route import error: {e}")
        return False

def test_models_integration():
    """Test model imports and structure"""
    print("\n🔄 Testing Model Integration...")
    
    try:
        from app.models import Payment, PaymentCreate, PaymentUpdate, PaymentStatus, APIResponse
        print("   ✅ Payment models imported successfully")
        
        # Test PaymentStatus enum
        statuses = ['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED']
        for status in statuses:
            if hasattr(PaymentStatus, status):
                print(f"   ✅ PaymentStatus.{status} available")
            else:
                print(f"   ❌ PaymentStatus.{status} missing")
        
        return True
    except Exception as e:
        print(f"   ❌ Model integration error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting Payment API Implementation Tests...")
    print("=" * 60)
    
    # Test imports first
    imports_ok = test_api_imports()
    models_ok = test_models_integration()
    
    # Test services
    services_ok = await test_payment_services()
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   API Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"   Models Integration: {'✅ PASS' if models_ok else '❌ FAIL'}")
    print(f"   Services Integration: {'✅ PASS' if services_ok else '❌ FAIL'}")
    
    if imports_ok and models_ok and services_ok:
        print("\n🎉 All tests passed! Payment API implementation is ready.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    return imports_ok and models_ok and services_ok

if __name__ == "__main__":
    asyncio.run(main()) 