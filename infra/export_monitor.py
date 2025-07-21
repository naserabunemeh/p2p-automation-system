#!/usr/bin/env python3
"""
EventBridge Export Monitor for P2P Automation System
Scans for approved payments, validates S3 files, simulates Workday delivery.
"""

import boto3
import json
import logging
import argparse
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError
import sys
import os

# Configure logging
def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('export_monitor.log')
        ]
    )
    return logging.getLogger(__name__)

class ExportMonitor:
    """
    EventBridge Export Monitor for automated payment processing
    """
    
    def __init__(self, region_name: str = "us-east-1", dry_run: bool = False):
        self.region_name = region_name
        self.dry_run = dry_run
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize AWS clients
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.s3_client = boto3.client('s3', region_name=region_name)
        
        # Table references
        self.payments_table = self.dynamodb.Table('PaymentsTable')
        self.audit_log_table = self.dynamodb.Table('AuditLogTable')
        
        # S3 bucket name
        self.s3_bucket = "p2p-automation-payments"
        
        # API endpoint for Workday callback (assuming local development)
        self.workday_callback_url = "http://localhost:8000/api/v1/workday/callback"
        
        # Monitor statistics
        self.stats = {
            'payments_scanned': 0,
            'approved_payments_found': 0,
            'files_validated': 0,
            'missing_files': 0,
            'workday_callbacks_sent': 0,
            'workday_callbacks_failed': 0,
            'errors': []
        }
    
    def scan_approved_payments(self) -> List[Dict[str, Any]]:
        """
        Scan PaymentsTable for payments with status == "approved"
        """
        try:
            self.logger.info("Scanning PaymentsTable for approved payments...")
            
            # Scan for approved payments that haven't been confirmed by Workday
            response = self.payments_table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('status').eq('approved') &
                               boto3.dynamodb.conditions.Attr('workday_callback_received').not_exists()
            )
            
            payments = response.get('Items', [])
            self.stats['payments_scanned'] = len(payments)
            self.stats['approved_payments_found'] = len([p for p in payments if p.get('status') == 'approved'])
            
            self.logger.info(f"Found {len(payments)} approved payments pending Workday confirmation")
            
            return payments
            
        except ClientError as e:
            error_msg = f"Error scanning payments table: {str(e)}"
            self.logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return []
    
    def validate_s3_files(self, payment: Dict[str, Any]) -> Dict[str, bool]:
        """
        Check S3 to confirm both XML and JSON files exist for a payment
        """
        payment_id = payment.get('id', '')
        xml_s3_key = payment.get('xml_s3_key', '')
        json_s3_key = payment.get('json_s3_key', '')
        
        validation_result = {
            'xml_exists': False,
            'json_exists': False,
            'both_exist': False
        }
        
        try:
            # Check XML file
            if xml_s3_key:
                try:
                    self.s3_client.head_object(Bucket=self.s3_bucket, Key=xml_s3_key)
                    validation_result['xml_exists'] = True
                    self.logger.debug(f"XML file exists for payment {payment_id}: {xml_s3_key}")
                except ClientError:
                    self.logger.warning(f"XML file missing for payment {payment_id}: {xml_s3_key}")
            
            # Check JSON file
            if json_s3_key:
                try:
                    self.s3_client.head_object(Bucket=self.s3_bucket, Key=json_s3_key)
                    validation_result['json_exists'] = True
                    self.logger.debug(f"JSON file exists for payment {payment_id}: {json_s3_key}")
                except ClientError:
                    self.logger.warning(f"JSON file missing for payment {payment_id}: {json_s3_key}")
            
            validation_result['both_exist'] = validation_result['xml_exists'] and validation_result['json_exists']
            
            if validation_result['both_exist']:
                self.stats['files_validated'] += 1
            else:
                self.stats['missing_files'] += 1
                
            return validation_result
            
        except Exception as e:
            error_msg = f"Error validating S3 files for payment {payment_id}: {str(e)}"
            self.logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return validation_result
    
    def simulate_workday_delivery(self, payment: Dict[str, Any]) -> bool:
        """
        Simulate export delivery by POSTing to /workday/callback
        """
        payment_id = payment.get('id', '')
        
        if self.dry_run:
            self.logger.info(f"[DRY-RUN] Would send Workday callback for payment {payment_id}")
            return True
        
        try:
            callback_payload = {
                "payment_id": payment_id,
                "status": "sent"
            }
            
            self.logger.info(f"Sending Workday callback for payment {payment_id}")
            
            response = requests.post(
                self.workday_callback_url,
                json=callback_payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.info(f"Workday callback successful for payment {payment_id}")
                self.stats['workday_callbacks_sent'] += 1
                return True
            else:
                error_msg = f"Workday callback failed for payment {payment_id}: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                self.stats['workday_callbacks_failed'] += 1
                self.stats['errors'].append(error_msg)
                return False
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error sending Workday callback for payment {payment_id}: {str(e)}"
            self.logger.error(error_msg)
            self.stats['workday_callbacks_failed'] += 1
            self.stats['errors'].append(error_msg)
            return False
        except Exception as e:
            error_msg = f"Unexpected error sending Workday callback for payment {payment_id}: {str(e)}"
            self.logger.error(error_msg)
            self.stats['workday_callbacks_failed'] += 1
            self.stats['errors'].append(error_msg)
            return False
    
    def log_monitor_action(self, action: str, details: Dict[str, Any]):
        """
        Log monitor actions to AuditLogTable
        """
        try:
            if self.dry_run:
                self.logger.debug(f"[DRY-RUN] Would log audit action: {action}")
                return
            
            import uuid
            from decimal import Decimal
            
            # Convert floats to Decimal for DynamoDB
            def convert_floats(obj):
                if isinstance(obj, dict):
                    return {k: convert_floats(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_floats(v) for v in obj]
                elif isinstance(obj, float):
                    return Decimal(str(obj))
                else:
                    return obj
            
            audit_entry = {
                'id': str(uuid.uuid4()),
                'type': 'EXPORT_MONITOR',
                'action': action,
                'entity_type': 'ExportMonitor',
                'entity_id': 'scheduled_job',
                'user_id': 'system',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'details': convert_floats(details),
                'workday_url': self.workday_callback_url,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            self.audit_log_table.put_item(Item=audit_entry)
            self.logger.debug(f"Audit log created: {action}")
            
        except Exception as e:
            error_msg = f"Error creating audit log for action {action}: {str(e)}"
            self.logger.error(error_msg)
            self.stats['errors'].append(error_msg)
    
    def generate_daily_report(self) -> Dict[str, Any]:
        """
        Generate daily report summary
        """
        report = {
            'report_timestamp': datetime.now(timezone.utc).isoformat(),
            'monitor_run_stats': self.stats.copy(),
            'summary': {
                'success_rate': 0,
                'files_validation_rate': 0,
                'workday_delivery_rate': 0
            }
        }
        
        # Calculate success rates
        if self.stats['approved_payments_found'] > 0:
            report['summary']['files_validation_rate'] = (
                self.stats['files_validated'] / self.stats['approved_payments_found'] * 100
            )
            
            if self.stats['files_validated'] > 0:
                report['summary']['workday_delivery_rate'] = (
                    self.stats['workday_callbacks_sent'] / self.stats['files_validated'] * 100
                )
        
        report['summary']['success_rate'] = (
            self.stats['workday_callbacks_sent'] / max(1, self.stats['approved_payments_found']) * 100
        )
        
        return report
    
    def run_monitor_cycle(self) -> Dict[str, Any]:
        """
        Run a complete monitor cycle
        """
        cycle_start = datetime.now(timezone.utc)
        self.logger.info(f"Starting export monitor cycle at {cycle_start}")
        
        try:
            # Log monitor start
            self.log_monitor_action("MONITOR_START", {
                "cycle_start": cycle_start.isoformat(),
                "dry_run": self.dry_run,
                "region": self.region_name
            })
            
            # Step 1: Scan for approved payments
            approved_payments = self.scan_approved_payments()
            
            # Step 2: Process each approved payment
            for payment in approved_payments:
                payment_id = payment.get('id', '')
                self.logger.info(f"Processing payment {payment_id}")
                
                # Validate S3 files exist
                file_validation = self.validate_s3_files(payment)
                
                if file_validation['both_exist']:
                    self.logger.info(f"Both XML and JSON files exist for payment {payment_id}")
                    
                    # Simulate Workday delivery
                    delivery_success = self.simulate_workday_delivery(payment)
                    
                    if delivery_success:
                        self.log_monitor_action("WORKDAY_DELIVERY_SUCCESS", {
                            "payment_id": payment_id,
                            "vendor_id": payment.get('vendor_id'),
                            "invoice_id": payment.get('invoice_id'),
                            "amount": payment.get('amount'),
                            "xml_s3_key": payment.get('xml_s3_key'),
                            "json_s3_key": payment.get('json_s3_key')
                        })
                    else:
                        self.log_monitor_action("WORKDAY_DELIVERY_FAILED", {
                            "payment_id": payment_id,
                            "error": "Callback request failed"
                        })
                else:
                    self.logger.warning(f"Missing S3 files for payment {payment_id}")
                    self.log_monitor_action("FILES_MISSING", {
                        "payment_id": payment_id,
                        "xml_exists": file_validation['xml_exists'],
                        "json_exists": file_validation['json_exists'],
                        "xml_s3_key": payment.get('xml_s3_key'),
                        "json_s3_key": payment.get('json_s3_key')
                    })
            
            # Step 3: Generate daily report
            report = self.generate_daily_report()
            
            # Log monitor completion
            cycle_end = datetime.now(timezone.utc)
            cycle_duration = (cycle_end - cycle_start).total_seconds()
            
            self.log_monitor_action("MONITOR_COMPLETE", {
                "cycle_end": cycle_end.isoformat(),
                "cycle_duration_seconds": cycle_duration,
                "report": report
            })
            
            self.logger.info(f"Export monitor cycle completed in {cycle_duration:.2f} seconds")
            self.logger.info(f"Summary: {self.stats['approved_payments_found']} approved payments, "
                           f"{self.stats['files_validated']} validated, "
                           f"{self.stats['workday_callbacks_sent']} delivered to Workday")
            
            return report
            
        except Exception as e:
            error_msg = f"Error in monitor cycle: {str(e)}"
            self.logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            
            self.log_monitor_action("MONITOR_ERROR", {
                "error": error_msg,
                "cycle_start": cycle_start.isoformat()
            })
            
            raise

def main():
    """
    Main entry point for the export monitor
    """
    parser = argparse.ArgumentParser(description="P2P Export Monitor")
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no actual changes)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--workday-url', default='http://localhost:8000/api/v1/workday/callback',
                       help='Workday callback URL')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level)
    
    try:
        logger.info("Starting P2P Export Monitor")
        logger.info(f"Configuration: region={args.region}, dry_run={args.dry_run}, log_level={args.log_level}")
        
        # Create and run monitor
        monitor = ExportMonitor(region_name=args.region, dry_run=args.dry_run)
        monitor.workday_callback_url = args.workday_url
        
        report = monitor.run_monitor_cycle()
        
        # Print report summary
        print("\n" + "="*60)
        print("P2P EXPORT MONITOR REPORT")
        print("="*60)
        print(f"Timestamp: {report['report_timestamp']}")
        print(f"Approved Payments: {report['monitor_run_stats']['approved_payments_found']}")
        print(f"Files Validated: {report['monitor_run_stats']['files_validated']}")
        print(f"Workday Deliveries: {report['monitor_run_stats']['workday_callbacks_sent']}")
        print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
        print(f"Errors: {len(report['monitor_run_stats']['errors'])}")
        if report['monitor_run_stats']['errors']:
            print("\nErrors:")
            for error in report['monitor_run_stats']['errors']:
                print(f"  - {error}")
        print("="*60)
        
        # Save report to file
        report_filename = f"export_monitor_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report saved to {report_filename}")
        
    except KeyboardInterrupt:
        logger.info("Monitor interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Monitor failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 