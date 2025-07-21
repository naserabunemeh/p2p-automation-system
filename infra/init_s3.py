#!/usr/bin/env python3
"""
S3 Initialization Script for P2P Automation System

This script creates the necessary S3 buckets for the ERP-Lite P2P system.
Run this script once to initialize the storage infrastructure.

Usage:
    python init_s3.py [--region us-east-1] [--profile default] [--bucket-prefix p2p-automation]
"""

import boto3
import argparse
import sys
import json
from botocore.exceptions import ClientError, BotoCoreError

# Bucket configuration
BUCKET_CONFIG = {
    "payments": {
        "suffix": "payments",
        "description": "Payment XML/JSON files and related documents",
        "versioning": True,
        "lifecycle_rules": [
            {
                "Id": "payment-files-lifecycle",
                "Status": "Enabled",
                "Filter": {"Prefix": "payments/"},
                "Transitions": [
                    {
                        "Days": 30,
                        "StorageClass": "STANDARD_IA"
                    },
                    {
                        "Days": 90,
                        "StorageClass": "GLACIER"
                    },
                    {
                        "Days": 365,
                        "StorageClass": "DEEP_ARCHIVE"
                    }
                ]
            }
        ],
        "folders": [
            "payments/xml/",
            "payments/json/",
            "payments/processed/",
            "payments/failed/"
        ]
    },
    "documents": {
        "suffix": "documents",
        "description": "Invoice PDFs, contracts, and supporting documents",
        "versioning": True,
        "lifecycle_rules": [
            {
                "Id": "documents-lifecycle",
                "Status": "Enabled",
                "Filter": {"Prefix": "documents/"},
                "Transitions": [
                    {
                        "Days": 90,
                        "StorageClass": "STANDARD_IA"
                    },
                    {
                        "Days": 365,
                        "StorageClass": "GLACIER"
                    }
                ]
            }
        ],
        "folders": [
            "documents/invoices/",
            "documents/contracts/",
            "documents/purchase_orders/",
            "documents/receipts/"
        ]
    },
    "backups": {
        "suffix": "backups",
        "description": "Database backups and system exports",
        "versioning": True,
        "lifecycle_rules": [
            {
                "Id": "backups-lifecycle",
                "Status": "Enabled",
                "Filter": {"Prefix": "backups/"},
                "Transitions": [
                    {
                        "Days": 7,
                        "StorageClass": "STANDARD_IA"
                    },
                    {
                        "Days": 30,
                        "StorageClass": "GLACIER"
                    }
                ],
                "Expiration": {
                    "Days": 2555  # 7 years retention
                }
            }
        ],
        "folders": [
            "backups/daily/",
            "backups/weekly/",
            "backups/monthly/",
            "backups/yearly/"
        ]
    },
    "reports": {
        "suffix": "reports",
        "description": "Generated reports and analytics data",
        "versioning": False,
        "lifecycle_rules": [
            {
                "Id": "reports-lifecycle",
                "Status": "Enabled",
                "Filter": {"Prefix": "reports/"},
                "Transitions": [
                    {
                        "Days": 30,
                        "StorageClass": "STANDARD_IA"
                    },
                    {
                        "Days": 180,
                        "StorageClass": "GLACIER"
                    }
                ],
                "Expiration": {
                    "Days": 1095  # 3 years retention
                }
            }
        ],
        "folders": [
            "reports/daily/",
            "reports/monthly/",
            "reports/quarterly/",
            "reports/annual/"
        ]
    }
}

def create_bucket(s3, bucket_name, region):
    """Create an S3 bucket"""
    try:
        if region == 'us-east-1':
            # us-east-1 doesn't need LocationConstraint
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        
        print(f"✓ Created bucket: {bucket_name}")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'BucketAlreadyOwnedByYou':
            print(f"⚠ Bucket {bucket_name} already exists and is owned by you")
            return True
        elif error_code == 'BucketAlreadyExists':
            print(f"✗ Bucket {bucket_name} already exists and is owned by someone else")
            return False
        else:
            print(f"✗ Error creating bucket {bucket_name}: {e}")
            return False
    except Exception as e:
        print(f"✗ Unexpected error creating bucket {bucket_name}: {e}")
        return False

def configure_bucket_versioning(s3, bucket_name, enabled=True):
    """Configure bucket versioning"""
    try:
        status = 'Enabled' if enabled else 'Suspended'
        s3.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': status}
        )
        print(f"✓ Versioning {status.lower()} for {bucket_name}")
        return True
        
    except Exception as e:
        print(f"✗ Error configuring versioning for {bucket_name}: {e}")
        return False

def configure_bucket_encryption(s3, bucket_name):
    """Configure bucket server-side encryption"""
    try:
        s3.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        },
                        'BucketKeyEnabled': True
                    }
                ]
            }
        )
        print(f"✓ Encryption enabled for {bucket_name}")
        return True
        
    except Exception as e:
        print(f"✗ Error configuring encryption for {bucket_name}: {e}")
        return False

def configure_bucket_lifecycle(s3, bucket_name, lifecycle_rules):
    """Configure bucket lifecycle rules"""
    try:
        s3.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration={'Rules': lifecycle_rules}
        )
        print(f"✓ Lifecycle rules configured for {bucket_name}")
        return True
        
    except Exception as e:
        print(f"✗ Error configuring lifecycle for {bucket_name}: {e}")
        return False

def configure_bucket_cors(s3, bucket_name):
    """Configure CORS for bucket"""
    cors_configuration = {
        'CORSRules': [
            {
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE'],
                'AllowedOrigins': ['*'],
                'ExposeHeaders': ['ETag'],
                'MaxAgeSeconds': 3000
            }
        ]
    }
    
    try:
        s3.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration=cors_configuration
        )
        print(f"✓ CORS configured for {bucket_name}")
        return True
        
    except Exception as e:
        print(f"✗ Error configuring CORS for {bucket_name}: {e}")
        return False

def create_folder_structure(s3, bucket_name, folders):
    """Create folder structure in bucket"""
    try:
        for folder in folders:
            # Create a placeholder object to represent the folder
            s3.put_object(
                Bucket=bucket_name,
                Key=folder + ".gitkeep",
                Body=b"# This file maintains the folder structure\n",
                ContentType="text/plain"
            )
        
        print(f"✓ Created folder structure in {bucket_name} ({len(folders)} folders)")
        return True
        
    except Exception as e:
        print(f"✗ Error creating folder structure in {bucket_name}: {e}")
        return False

def configure_bucket_policy(s3, bucket_name, environment):
    """Configure bucket policy for security"""
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DenyInsecureConnections",
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}/*",
                    f"arn:aws:s3:::{bucket_name}"
                ],
                "Condition": {
                    "Bool": {
                        "aws:SecureTransport": "false"
                    }
                }
            }
        ]
    }
    
    # Add more restrictive policies for production
    if environment.lower() == 'production':
        bucket_policy["Statement"].append({
            "Sid": "RestrictToApplicationAccess",
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": f"arn:aws:s3:::{bucket_name}/*",
            "Condition": {
                "StringEquals": {
                    "s3:x-amz-server-side-encryption": "AES256"
                }
            }
        })
    
    try:
        s3.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        print(f"✓ Security policy configured for {bucket_name}")
        return True
        
    except Exception as e:
        print(f"✗ Error configuring policy for {bucket_name}: {e}")
        return False

def configure_bucket_tags(s3, bucket_name, environment, bucket_type):
    """Configure bucket tags"""
    tags = {
        'Project': 'P2P-Automation',
        'Environment': environment.title(),
        'Owner': 'Finance-Team',
        'BucketType': bucket_type,
        'ManagedBy': 'P2P-System'
    }
    
    tag_set = [{'Key': k, 'Value': v} for k, v in tags.items()]
    
    try:
        s3.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={'TagSet': tag_set}
        )
        print(f"✓ Tags configured for {bucket_name}")
        return True
        
    except Exception as e:
        print(f"✗ Error configuring tags for {bucket_name}: {e}")
        return False

def verify_bucket_setup(s3, bucket_name):
    """Verify bucket configuration"""
    try:
        # Check bucket exists
        s3.head_bucket(Bucket=bucket_name)
        
        # Get bucket location
        location = s3.get_bucket_location(Bucket=bucket_name)
        region = location.get('LocationConstraint', 'us-east-1')
        
        # Get object count (approximate)
        paginator = s3.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=bucket_name)
        
        object_count = 0
        for page in page_iterator:
            object_count += page.get('KeyCount', 0)
        
        print(f"✓ Bucket {bucket_name} verification:")
        print(f"  Region: {region}")
        print(f"  Objects: {object_count}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error verifying bucket {bucket_name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Initialize S3 buckets for P2P Automation System')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--profile', default=None, help='AWS profile to use')
    parser.add_argument('--bucket-prefix', default='p2p-automation', help='Bucket name prefix')
    parser.add_argument('--environment', default='development', help='Environment tag (default: development)')
    parser.add_argument('--verify', action='store_true', help='Verify bucket configuration after creation')
    parser.add_argument('--skip-lifecycle', action='store_true', help='Skip lifecycle configuration')
    parser.add_argument('--skip-cors', action='store_true', help='Skip CORS configuration')
    
    args = parser.parse_args()
    
    print("🚀 P2P Automation System - S3 Initialization")
    print("=" * 50)
    print(f"Region: {args.region}")
    print(f"Environment: {args.environment}")
    print(f"Bucket Prefix: {args.bucket_prefix}")
    print()
    
    try:
        # Initialize boto3 session
        session = boto3.Session(profile_name=args.profile)
        s3 = session.client('s3', region_name=args.region)
        
        print("✓ Connected to AWS S3")
        print()
        
        # Create and configure buckets
        created_buckets = []
        failed_buckets = []
        
        for bucket_key, bucket_config in BUCKET_CONFIG.items():
            bucket_name = f"{args.bucket_prefix}-{bucket_config['suffix']}"
            print(f"Processing bucket: {bucket_name}")
            print(f"  Description: {bucket_config['description']}")
            
            # Create bucket
            if not create_bucket(s3, bucket_name, args.region):
                failed_buckets.append(bucket_name)
                continue
            
            # Configure versioning
            if bucket_config.get('versioning', False):
                configure_bucket_versioning(s3, bucket_name, True)
            
            # Configure encryption
            configure_bucket_encryption(s3, bucket_name)
            
            # Configure lifecycle rules
            if not args.skip_lifecycle and bucket_config.get('lifecycle_rules'):
                configure_bucket_lifecycle(s3, bucket_name, bucket_config['lifecycle_rules'])
            
            # Configure CORS
            if not args.skip_cors:
                configure_bucket_cors(s3, bucket_name)
            
            # Configure security policy
            configure_bucket_policy(s3, bucket_name, args.environment)
            
            # Configure tags
            configure_bucket_tags(s3, bucket_name, args.environment, bucket_key)
            
            # Create folder structure
            if bucket_config.get('folders'):
                create_folder_structure(s3, bucket_name, bucket_config['folders'])
            
            created_buckets.append(bucket_name)
            print()
        
        print("=" * 50)
        print(f"✓ Successfully created: {len(created_buckets)} buckets")
        print(f"✗ Failed: {len(failed_buckets)} buckets")
        
        if failed_buckets:
            print(f"Failed buckets: {', '.join(failed_buckets)}")
            return 1
        
        # Verify bucket setup if requested
        if args.verify:
            print()
            print("Verifying bucket configuration...")
            
            for bucket_name in created_buckets:
                verify_bucket_setup(s3, bucket_name)
        
        print()
        print("🎉 S3 initialization completed successfully!")
        print()
        print("Bucket Summary:")
        for bucket_name in created_buckets:
            print(f"  • {bucket_name}")
        
        print()
        print("Next steps:")
        print("1. Update your application configuration with bucket names")
        print("2. Test file upload/download functionality")
        print("3. Configure CloudFront distribution if needed")
        
        return 0
        
    except (BotoCoreError, ClientError) as e:
        print(f"✗ AWS Error: {e}")
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 