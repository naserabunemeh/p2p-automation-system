import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class S3Service:
    """Service class for S3 operations"""
    
    def __init__(self, region_name: str = "us-east-1"):
        self.s3_client = boto3.client('s3', region_name=region_name)
        self.region_name = region_name
        # S3 bucket name from the AWS resources documentation
        self.bucket_name = "p2p-payment-xml-storage-20250721-005155-6839"
    
    async def upload_payment_file(self, 
                                payment_id: str, 
                                content: str, 
                                file_format: str,
                                payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upload payment file (XML or JSON) to S3 with metadata tags
        
        Args:
            payment_id: Payment ID for the file
            content: File content (XML or JSON string)
            file_format: File format ('xml' or 'json')
            payment_data: Payment data for metadata tags
            
        Returns:
            Dictionary with upload details
        """
        try:
            # Generate file key
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            file_key = f"payments/{payment_id}/payment_{payment_id}_{timestamp}.{file_format}"
            
            # Prepare metadata tags
            metadata = {
                'payment_id': str(payment_data.get('id', payment_id)),
                'invoice_id': str(payment_data.get('invoice_id', '')),
                'vendor_id': str(payment_data.get('vendor_id', '')),
                'payment_amount': str(payment_data.get('payment_amount', '0.00')),
                'payment_method': str(payment_data.get('payment_method', 'ACH')),
                'reference_number': str(payment_data.get('reference_number', '')),
                'status': str(payment_data.get('status', '')),
                'processed_by': str(payment_data.get('processed_by', '')),
                'file_format': file_format,
                'upload_timestamp': datetime.utcnow().isoformat(),
                'content_type': f'application/{file_format}'
            }
            
            # Convert metadata to tags format for S3
            tag_set = []
            for key, value in metadata.items():
                if value and len(str(value)) > 0:  # Only add non-empty values
                    # S3 tag values must be URL encoded if they contain special characters
                    tag_set.append({'Key': key, 'Value': str(value)[:256]})  # S3 tag values limited to 256 chars
            
            # Upload file to S3
            response = self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=content.encode('utf-8'),
                ContentType=f'application/{file_format}',
                Metadata=metadata,
                ServerSideEncryption='AES256',
                TaggingDirective='REPLACE' if tag_set else None
            )
            
            # Add tags to the object if we have any
            if tag_set:
                self.s3_client.put_object_tagging(
                    Bucket=self.bucket_name,
                    Key=file_key,
                    Tagging={'TagSet': tag_set}
                )
            
            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{file_key}"
            
            logger.info(f"Uploaded {file_format.upper()} file for payment {payment_id} to S3: {file_key}")
            
            return {
                'success': True,
                'bucket': self.bucket_name,
                'key': file_key,
                'url': s3_url,
                'etag': response.get('ETag', '').strip('"'),
                'version_id': response.get('VersionId'),
                'file_format': file_format,
                'metadata': metadata,
                'upload_timestamp': metadata['upload_timestamp']
            }
            
        except ClientError as e:
            error_msg = f"Failed to upload {file_format} file for payment {payment_id}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_code': e.response.get('Error', {}).get('Code', 'Unknown')
            }
        except Exception as e:
            error_msg = f"Unexpected error uploading file for payment {payment_id}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    async def get_payment_file(self, file_key: str) -> Dict[str, Any]:
        """
        Retrieve payment file from S3
        
        Args:
            file_key: S3 object key
            
        Returns:
            Dictionary with file details and content
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            
            content = response['Body'].read().decode('utf-8')
            
            return {
                'success': True,
                'content': content,
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag', '').strip('"'),
                'metadata': response.get('Metadata', {}),
                'file_key': file_key
            }
            
        except ClientError as e:
            error_msg = f"Failed to retrieve file {file_key}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_code': e.response.get('Error', {}).get('Code', 'Unknown')
            }
    
    async def list_payment_files(self, payment_id: str) -> Dict[str, Any]:
        """
        List all files for a specific payment
        
        Args:
            payment_id: Payment ID to list files for
            
        Returns:
            Dictionary with list of files
        """
        try:
            prefix = f"payments/{payment_id}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                # Get object metadata and tags
                try:
                    obj_metadata = self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=obj['Key']
                    )
                    
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'etag': obj['ETag'].strip('"'),
                        'metadata': obj_metadata.get('Metadata', {}),
                        'content_type': obj_metadata.get('ContentType')
                    })
                except ClientError:
                    # If we can't get metadata, still include basic info
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'etag': obj['ETag'].strip('"')
                    })
            
            return {
                'success': True,
                'payment_id': payment_id,
                'files': files,
                'file_count': len(files)
            }
            
        except ClientError as e:
            error_msg = f"Failed to list files for payment {payment_id}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_code': e.response.get('Error', {}).get('Code', 'Unknown')
            }
    
    async def delete_payment_file(self, file_key: str) -> Dict[str, Any]:
        """
        Delete payment file from S3
        
        Args:
            file_key: S3 object key to delete
            
        Returns:
            Dictionary with deletion status
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            
            logger.info(f"Deleted payment file: {file_key}")
            
            return {
                'success': True,
                'message': f"File {file_key} deleted successfully"
            }
            
        except ClientError as e:
            error_msg = f"Failed to delete file {file_key}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_code': e.response.get('Error', {}).get('Code', 'Unknown')
            }

# Global service instance
s3_service = S3Service() 