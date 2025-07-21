#!/usr/bin/env python3
"""
DynamoDB Initialization Script for P2P Automation System

This script creates the necessary DynamoDB tables for the ERP-Lite P2P system.
Run this script once to initialize the database structure.

Usage:
    python init_dynamodb.py [--region us-east-1] [--profile default]
"""

import boto3
import argparse
import sys
import time
from botocore.exceptions import ClientError, BotoCoreError

# Table configuration
TABLE_CONFIG = {
    "vendors": {
        "TableName": "p2p_vendors",
        "KeySchema": [
            {"AttributeName": "id", "KeyType": "HASH"}
        ],
        "AttributeDefinitions": [
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"}
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "status-created_at-index",
                "KeySchema": [
                    {"AttributeName": "status", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            }
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "Tags": [
            {"Key": "Project", "Value": "P2P-Automation"},
            {"Key": "Environment", "Value": "Development"},
            {"Key": "Owner", "Value": "Finance-Team"}
        ]
    },
    "purchase_orders": {
        "TableName": "p2p_purchase_orders",
        "KeySchema": [
            {"AttributeName": "id", "KeyType": "HASH"}
        ],
        "AttributeDefinitions": [
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "vendor_id", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
            {"AttributeName": "po_number", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"}
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "vendor_id-created_at-index",
                "KeySchema": [
                    {"AttributeName": "vendor_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            },
            {
                "IndexName": "status-created_at-index",
                "KeySchema": [
                    {"AttributeName": "status", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            },
            {
                "IndexName": "po_number-index",
                "KeySchema": [
                    {"AttributeName": "po_number", "KeyType": "HASH"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            }
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "Tags": [
            {"Key": "Project", "Value": "P2P-Automation"},
            {"Key": "Environment", "Value": "Development"},
            {"Key": "Owner", "Value": "Finance-Team"}
        ]
    },
    "invoices": {
        "TableName": "p2p_invoices",
        "KeySchema": [
            {"AttributeName": "id", "KeyType": "HASH"}
        ],
        "AttributeDefinitions": [
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "vendor_id", "AttributeType": "S"},
            {"AttributeName": "po_id", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
            {"AttributeName": "invoice_number", "AttributeType": "S"},
            {"AttributeName": "due_date", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"}
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "vendor_id-created_at-index",
                "KeySchema": [
                    {"AttributeName": "vendor_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            },
            {
                "IndexName": "po_id-created_at-index",
                "KeySchema": [
                    {"AttributeName": "po_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            },
            {
                "IndexName": "status-due_date-index",
                "KeySchema": [
                    {"AttributeName": "status", "KeyType": "HASH"},
                    {"AttributeName": "due_date", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            },
            {
                "IndexName": "invoice_number-index",
                "KeySchema": [
                    {"AttributeName": "invoice_number", "KeyType": "HASH"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            }
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "Tags": [
            {"Key": "Project", "Value": "P2P-Automation"},
            {"Key": "Environment", "Value": "Development"},
            {"Key": "Owner", "Value": "Finance-Team"}
        ]
    },
    "payments": {
        "TableName": "p2p_payments",
        "KeySchema": [
            {"AttributeName": "id", "KeyType": "HASH"}
        ],
        "AttributeDefinitions": [
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "invoice_id", "AttributeType": "S"},
            {"AttributeName": "vendor_id", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
            {"AttributeName": "payment_date", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"}
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "invoice_id-index",
                "KeySchema": [
                    {"AttributeName": "invoice_id", "KeyType": "HASH"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            },
            {
                "IndexName": "vendor_id-payment_date-index",
                "KeySchema": [
                    {"AttributeName": "vendor_id", "KeyType": "HASH"},
                    {"AttributeName": "payment_date", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            },
            {
                "IndexName": "status-created_at-index",
                "KeySchema": [
                    {"AttributeName": "status", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            }
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "Tags": [
            {"Key": "Project", "Value": "P2P-Automation"},
            {"Key": "Environment", "Value": "Development"},
            {"Key": "Owner", "Value": "Finance-Team"}
        ]
    }
}

def create_table(dynamodb, table_name, table_config):
    """Create a DynamoDB table with the given configuration"""
    try:
        print(f"Creating table: {table_name}")
        
        response = dynamodb.create_table(**table_config)
        
        print(f"✓ Table {table_name} creation initiated")
        print(f"  Table ARN: {response['TableDescription']['TableArn']}")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceInUseException':
            print(f"⚠ Table {table_name} already exists")
            return True
        else:
            print(f"✗ Error creating table {table_name}: {e}")
            return False
    except Exception as e:
        print(f"✗ Unexpected error creating table {table_name}: {e}")
        return False

def wait_for_table_creation(dynamodb, table_name, max_wait_time=300):
    """Wait for table to become active"""
    print(f"Waiting for table {table_name} to become active...")
    
    start_time = time.time()
    waiter = dynamodb.get_waiter('table_exists')
    
    try:
        waiter.wait(
            TableName=table_name,
            WaiterConfig={
                'Delay': 10,
                'MaxAttempts': max_wait_time // 10
            }
        )
        
        elapsed_time = time.time() - start_time
        print(f"✓ Table {table_name} is now active (took {elapsed_time:.1f}s)")
        return True
        
    except Exception as e:
        print(f"✗ Timeout waiting for table {table_name}: {e}")
        return False

def verify_table_setup(dynamodb, table_name):
    """Verify table is properly configured"""
    try:
        response = dynamodb.describe_table(TableName=table_name)
        table_desc = response['TableDescription']
        
        print(f"✓ Table {table_name} verification:")
        print(f"  Status: {table_desc['TableStatus']}")
        print(f"  Items: {table_desc.get('ItemCount', 0)}")
        print(f"  Size: {table_desc.get('TableSizeBytes', 0)} bytes")
        
        # Check GSIs
        gsi_count = len(table_desc.get('GlobalSecondaryIndexes', []))
        print(f"  Global Secondary Indexes: {gsi_count}")
        
        for gsi in table_desc.get('GlobalSecondaryIndexes', []):
            print(f"    - {gsi['IndexName']}: {gsi['IndexStatus']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error verifying table {table_name}: {e}")
        return False

def enable_point_in_time_recovery(dynamodb, table_name):
    """Enable point-in-time recovery for the table"""
    try:
        dynamodb.update_continuous_backups(
            TableName=table_name,
            PointInTimeRecoverySpecification={
                'PointInTimeRecoveryEnabled': True
            }
        )
        print(f"✓ Point-in-time recovery enabled for {table_name}")
        return True
        
    except Exception as e:
        print(f"⚠ Could not enable point-in-time recovery for {table_name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Initialize DynamoDB tables for P2P Automation System')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--profile', default=None, help='AWS profile to use')
    parser.add_argument('--environment', default='development', help='Environment tag (default: development)')
    parser.add_argument('--wait', action='store_true', help='Wait for tables to become active')
    parser.add_argument('--verify', action='store_true', help='Verify table configuration after creation')
    parser.add_argument('--enable-pitr', action='store_true', help='Enable point-in-time recovery')
    
    args = parser.parse_args()
    
    print("🚀 P2P Automation System - DynamoDB Initialization")
    print("=" * 55)
    print(f"Region: {args.region}")
    print(f"Environment: {args.environment}")
    print()
    
    # Update environment tags
    for table_config in TABLE_CONFIG.values():
        for tag in table_config['Tags']:
            if tag['Key'] == 'Environment':
                tag['Value'] = args.environment.title()
    
    try:
        # Initialize boto3 session
        session = boto3.Session(profile_name=args.profile)
        dynamodb = session.client('dynamodb', region_name=args.region)
        
        print("✓ Connected to AWS DynamoDB")
        print()
        
        # Create tables
        created_tables = []
        failed_tables = []
        
        for table_key, table_config in TABLE_CONFIG.items():
            table_name = table_config['TableName']
            
            if create_table(dynamodb, table_name, table_config):
                created_tables.append(table_name)
            else:
                failed_tables.append(table_name)
        
        print()
        print("=" * 55)
        print(f"✓ Successfully initiated: {len(created_tables)} tables")
        print(f"✗ Failed: {len(failed_tables)} tables")
        
        if failed_tables:
            print(f"Failed tables: {', '.join(failed_tables)}")
            return 1
        
        # Wait for table creation if requested
        if args.wait and created_tables:
            print()
            print("Waiting for tables to become active...")
            
            for table_name in created_tables:
                if not wait_for_table_creation(dynamodb, table_name):
                    print(f"⚠ Table {table_name} may not be ready")
        
        # Verify table setup if requested
        if args.verify:
            print()
            print("Verifying table configuration...")
            
            for table_name in created_tables:
                verify_table_setup(dynamodb, table_name)
        
        # Enable point-in-time recovery if requested
        if args.enable_pitr:
            print()
            print("Enabling point-in-time recovery...")
            
            for table_name in created_tables:
                enable_point_in_time_recovery(dynamodb, table_name)
        
        print()
        print("🎉 DynamoDB initialization completed successfully!")
        print()
        print("Next steps:")
        print("1. Run the FastAPI application: python backend/app/main.py")
        print("2. Test the API endpoints: http://localhost:8000/docs")
        print("3. Initialize S3 buckets: python infra/init_s3.py")
        
        return 0
        
    except (BotoCoreError, ClientError) as e:
        print(f"✗ AWS Error: {e}")
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 