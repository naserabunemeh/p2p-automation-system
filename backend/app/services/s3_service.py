import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging
import json

logger = logging.getLogger(__name__)

class S3Service:
    """Service class for S3 operations"""
    
    def __init__(self, region_name: str = "us-east-1"):
        self.s3_client = boto3.client('s3', region_name=region_name)
        self.region_name = region_name
        # S3 bucket name from the initialized infrastructure
        self.bucket_name = "p2p-automation-payments"
    
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
            # Generate file key - exact format as specified: payments/{payment_id}/payment.xml|.json
            file_key = f"payments/{payment_id}/payment.{file_format}"
            
            # Prepare metadata tags - as specified: invoice_id, vendor_id, amount, status
            metadata = {
                'payment_id': str(payment_data.get('id', payment_id)),
                'invoice_id': str(payment_data.get('invoice_id', '')),
                'vendor_id': str(payment_data.get('vendor_id', '')),
                'amount': str(payment_data.get('amount', '0.00')),
                'status': str(payment_data.get('status', '')),
                'file_format': file_format,
                'upload_timestamp': datetime.now(timezone.utc).isoformat(),
                'content_type': f'application/{file_format}'
            }
            
            # Convert metadata to tags format for S3
            tag_set = []
            for key, value in metadata.items():
                if value and len(str(value)) > 0:  # Only add non-empty values
                    # S3 tag values must be URL encoded if they contain special characters
                    tag_set.append({'Key': key, 'Value': str(value)[:256]})  # S3 tag values limited to 256 chars
            
            # Upload file to S3
            put_object_kwargs = {
                'Bucket': self.bucket_name,
                'Key': file_key,
                'Body': content.encode('utf-8'),
                'ContentType': f'application/{file_format}',
                'Metadata': metadata,
                'ServerSideEncryption': 'AES256'
            }
            
            # Add tagging if we have tags (during put_object)
            if tag_set:
                tag_string = '&'.join([f"{tag['Key']}={tag['Value']}" for tag in tag_set])
                put_object_kwargs['Tagging'] = tag_string
            
            response = self.s3_client.put_object(**put_object_kwargs)
            
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

    async def list_all_payment_files(self, 
                                   start_date: Optional[str] = None,
                                   end_date: Optional[str] = None,
                                   vendor_id: Optional[str] = None,
                                   status: Optional[str] = None,
                                   file_type: Optional[str] = None) -> Dict[str, Any]:
        """
        List all payment files in S3 with optional filters
        
        Args:
            start_date: Filter files uploaded after this date (ISO format)
            end_date: Filter files uploaded before this date (ISO format)
            vendor_id: Filter by vendor ID
            status: Filter by payment status
            file_type: Filter by file type ('xml' or 'json')
            
        Returns:
            Dictionary with list of all payment files and metadata
        """
        try:
            # List all objects in the payments prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix="payments/"
            )
            
            all_files = []
            
            for obj in response.get('Contents', []):
                # Skip .gitkeep files and directories
                if obj['Key'].endswith('.gitkeep') or obj['Key'].endswith('/'):
                    continue
                    
                try:
                    # Get object metadata and tags
                    obj_metadata = self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=obj['Key']
                    )
                    
                    # Get object tags
                    tags = {}
                    try:
                        tags_response = self.s3_client.get_object_tagging(
                            Bucket=self.bucket_name,
                            Key=obj['Key']
                        )
                        tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagSet', [])}
                    except ClientError:
                        # If tags can't be retrieved, continue without them
                        pass
                    
                    # Extract payment_id from key (payments/{payment_id}/payment.{format})
                    key_parts = obj['Key'].split('/')
                    payment_id = key_parts[1] if len(key_parts) >= 2 else 'unknown'
                    
                    # Determine file type from key
                    file_format = 'xml' if obj['Key'].endswith('.xml') else 'json' if obj['Key'].endswith('.json') else 'unknown'
                    
                    file_info = {
                        'key': obj['Key'],
                        'payment_id': payment_id,
                        'file_type': file_format,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'etag': obj['ETag'].strip('"'),
                        'metadata': obj_metadata.get('Metadata', {}),
                        'content_type': obj_metadata.get('ContentType'),
                        'tags': tags,
                        'vendor_id': tags.get('vendor_id', ''),
                        'invoice_id': tags.get('invoice_id', ''),
                        'amount': tags.get('amount', ''),
                        'payment_status': tags.get('status', ''),
                        'upload_timestamp': tags.get('upload_timestamp', '')
                    }
                    
                    # Apply filters
                    if start_date and file_info['upload_timestamp']:
                        try:
                            upload_time = datetime.fromisoformat(file_info['upload_timestamp'].replace('Z', '+00:00'))
                            filter_start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                            if upload_time < filter_start:
                                continue
                        except ValueError:
                            # If date parsing fails, skip this filter
                            pass
                    
                    if end_date and file_info['upload_timestamp']:
                        try:
                            upload_time = datetime.fromisoformat(file_info['upload_timestamp'].replace('Z', '+00:00'))
                            filter_end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                            if upload_time > filter_end:
                                continue
                        except ValueError:
                            # If date parsing fails, skip this filter
                            pass
                    
                    if vendor_id and file_info['vendor_id'] != vendor_id:
                        continue
                    
                    if status and file_info['payment_status'] != status:
                        continue
                    
                    if file_type and file_info['file_type'] != file_type:
                        continue
                    
                    all_files.append(file_info)
                    
                except ClientError:
                    # If we can't get metadata for a file, skip it
                    continue
            
            # Sort by last_modified descending (newest first)
            all_files.sort(key=lambda x: x['last_modified'], reverse=True)
            
            return {
                'success': True,
                'files': all_files,
                'file_count': len(all_files),
                'filters_applied': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'vendor_id': vendor_id,
                    'status': status,
                    'file_type': file_type
                }
            }
            
        except ClientError as e:
            error_msg = f"Failed to list all payment files: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_code': e.response.get('Error', {}).get('Code', 'Unknown')
            }

# Global service instance
s3_service = S3Service() 