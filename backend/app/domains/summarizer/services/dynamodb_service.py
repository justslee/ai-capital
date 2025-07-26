"""
DynamoDB Service for Summarization Metadata

Replaces PostgreSQL storage for summary metadata with cost-effective DynamoDB.
Handles section summaries, comprehensive reports, and processing status.
"""

import boto3
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
import json
from botocore.exceptions import ClientError

from ..config import get_summarization_config
from ..models.metadata import FilingMetadata, ChunkMetadata

logger = logging.getLogger(__name__)


class DynamoDBSummaryService:
    """DynamoDB service for storing summarization metadata."""
    
    def __init__(self):
        self.config = get_summarization_config()
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = 'summarization_metadata'
        self.table = self.dynamodb.Table(self.table_name)
    
    async def create_table_if_not_exists(self):
        """Create DynamoDB table if it doesn't exist."""
        try:
            # Check if table exists
            self.table.load()
            logger.info(f"DynamoDB table {self.table_name} already exists")
        except self.dynamodb.meta.client.exceptions.ResourceNotFoundException:
            # Create table
            table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {'AttributeName': 'PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'SK', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'PK', 'AttributeType': 'S'},
                    {'AttributeName': 'SK', 'AttributeType': 'S'},
                    {'AttributeName': 'ticker', 'AttributeType': 'S'},
                    {'AttributeName': 'filing_date', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'ticker-filing_date-index',
                        'KeySchema': [
                            {'AttributeName': 'ticker', 'KeyType': 'HASH'},
                            {'AttributeName': 'filing_date', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            table.wait_until_exists()
            logger.info(f"Created DynamoDB table {self.table_name}")
    
    def _convert_decimals(self, item: Dict) -> Dict:
        """Convert Decimal objects to float/int for JSON serialization."""
        if isinstance(item, dict):
            return {k: self._convert_decimals(v) for k, v in item.items()}
        elif isinstance(item, list):
            return [self._convert_decimals(v) for v in item]
        elif isinstance(item, Decimal):
            return float(item) if item % 1 else int(item)
        return item
    
    async def save_section_summary(
        self,
        accession_number: str,
        section_key: str,
        model_name: str,
        ticker: str = None,
        filing_date: str = None,
        form_type: str = None,
        s3_key: str = None,
        processing_status: str = "processing",
        tokens_used: int = None,
        file_size_kb: int = None,
        error_message: str = None,
        metadata: Dict = None
    ) -> bool:
        """Save section summary metadata to DynamoDB."""
        try:
            item = {
                'PK': f'FILING#{accession_number}',
                'SK': f'SUMMARY#{section_key}#{model_name}',
                'item_type': 'section_summary',
                'accession_number': accession_number,
                'section_key': section_key,
                'model_name': model_name,
                'processing_status': processing_status,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Add optional fields
            if ticker:
                item['ticker'] = ticker
            if filing_date:
                item['filing_date'] = filing_date
            if form_type:
                item['form_type'] = form_type
            if s3_key:
                item['s3_key'] = s3_key
            if tokens_used:
                item['tokens_used'] = tokens_used
            if file_size_kb:
                item['file_size_kb'] = file_size_kb
            if error_message:
                item['error_message'] = error_message
            if metadata:
                item['metadata'] = metadata
            
            self.table.put_item(Item=item)
            logger.info(f"Saved section summary: {accession_number}/{section_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving section summary: {e}")
            return False
    
    async def get_section_summary(
        self,
        accession_number: str,
        section_key: str,
        model_name: str
    ) -> Optional[Dict]:
        """Get section summary metadata from DynamoDB."""
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'FILING#{accession_number}',
                    'SK': f'SUMMARY#{section_key}#{model_name}'
                }
            )
            
            if 'Item' in response:
                return self._convert_decimals(response['Item'])
            return None
            
        except Exception as e:
            logger.error(f"Error getting section summary: {e}")
            return None
    
    async def save_comprehensive_report(
        self,
        accession_number: str,
        model_name: str,
        ticker: str = None,
        filing_date: str = None,
        form_type: str = None,
        s3_key: str = None,
        source_sections: List[str] = None,
        processing_status: str = "completed",
        tokens_used: int = None,
        file_size_kb: int = None,
        metadata: Dict = None
    ) -> bool:
        """Save comprehensive report metadata to DynamoDB."""
        try:
            item = {
                'PK': f'FILING#{accession_number}',
                'SK': f'REPORT#{model_name}',
                'item_type': 'comprehensive_report',
                'accession_number': accession_number,
                'model_name': model_name,
                'processing_status': processing_status,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Add optional fields
            if ticker:
                item['ticker'] = ticker
            if filing_date:
                item['filing_date'] = filing_date
            if form_type:
                item['form_type'] = form_type
            if s3_key:
                item['s3_key'] = s3_key
            if source_sections:
                item['source_sections'] = source_sections
            if tokens_used:
                item['tokens_used'] = tokens_used
            if file_size_kb:
                item['file_size_kb'] = file_size_kb
            if metadata:
                item['metadata'] = metadata
            
            self.table.put_item(Item=item)
            logger.info(f"Saved comprehensive report: {accession_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving comprehensive report: {e}")
            return False
    
    async def get_comprehensive_report(
        self,
        accession_number: str,
        model_name: str
    ) -> Optional[Dict]:
        """Get comprehensive report metadata from DynamoDB."""
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'FILING#{accession_number}',
                    'SK': f'REPORT#{model_name}'
                }
            )
            
            if 'Item' in response:
                return self._convert_decimals(response['Item'])
            return None
            
        except Exception as e:
            logger.error(f"Error getting comprehensive report: {e}")
            return None
    
    async def get_filing_summaries(self, accession_number: str) -> List[Dict]:
        """Get all summaries for a filing."""
        try:
            response = self.table.query(
                KeyConditionExpression='PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f'FILING#{accession_number}'
                }
            )
            
            items = response.get('Items', [])
            return [self._convert_decimals(item) for item in items]
            
        except Exception as e:
            logger.error(f"Error getting filing summaries: {e}")
            return []
    
    async def get_summaries_by_ticker(
        self,
        ticker: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get summaries by ticker using GSI."""
        try:
            response = self.table.query(
                IndexName='ticker-filing_date-index',
                KeyConditionExpression='ticker = :ticker',
                ExpressionAttributeValues={
                    ':ticker': ticker
                },
                Limit=limit,
                ScanIndexForward=False  # Sort by filing_date descending
            )
            
            items = response.get('Items', [])
            return [self._convert_decimals(item) for item in items]
            
        except Exception as e:
            logger.error(f"Error getting summaries by ticker: {e}")
            return []
    
    async def update_processing_status(
        self,
        accession_number: str,
        sk: str,
        status: str,
        error_message: str = None
    ) -> bool:
        """Update processing status for a summary or report."""
        try:
            update_expression = "SET processing_status = :status, updated_at = :updated"
            expression_values = {
                ':status': status,
                ':updated': datetime.now(timezone.utc).isoformat()
            }
            
            if error_message:
                update_expression += ", error_message = :error"
                expression_values[':error'] = error_message
            
            self.table.update_item(
                Key={
                    'PK': f'FILING#{accession_number}',
                    'SK': sk
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            logger.info(f"Updated status for {accession_number}/{sk}: {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            return False
    
    async def delete_filing_summaries(self, accession_number: str) -> bool:
        """Delete all summaries for a filing."""
        try:
            # Get all items for the filing
            summaries = await self.get_filing_summaries(accession_number)
            
            # Delete each item
            for summary in summaries:
                self.table.delete_item(
                    Key={
                        'PK': summary['PK'],
                        'SK': summary['SK']
                    }
                )
            
            logger.info(f"Deleted {len(summaries)} summaries for {accession_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting filing summaries: {e}")
            return False


# Singleton instance
_dynamodb_service = None

def get_dynamodb_summary_service() -> DynamoDBSummaryService:
    """Get singleton instance of DynamoDB summary service."""
    global _dynamodb_service
    if _dynamodb_service is None:
        _dynamodb_service = DynamoDBSummaryService()
    return _dynamodb_service 


class DynamoDBMetadataService:
    """
    Service to manage filing and summarization metadata in DynamoDB.
    """
    def __init__(self, table_name: str = "ai_capital_filing_metadata", region_name: str = "us-east-1"):
        """
        Initializes the DynamoDB service.

        :param table_name: The name of the DynamoDB table.
        :param region_name: The AWS region.
        """
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.table = self.dynamodb.Table(self.table_name)

    async def create_table_if_not_exists(self):
        """
        Creates the DynamoDB table if it does not already exist.
        This method is idempotent.
        """
        try:
            self.dynamodb.meta.client.describe_table(TableName=self.table_name)
            logger.info(f"Table '{self.table_name}' already exists.")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"Table '{self.table_name}' does not exist. Creating now...")
                self.dynamodb.create_table(
                    TableName=self.table_name,
                    KeySchema=[
                        {
                            'AttributeName': 'accession_number',
                            'KeyType': 'HASH'  # Partition key
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'accession_number',
                            'AttributeType': 'S'
                        }
                    ],
                    ProvisionedThroughput={
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                )
                self.table.wait_until_exists()
                logger.info(f"Table '{self.table_name}' created successfully.")
            else:
                logger.error(f"An unexpected error occurred: {e}")
                raise

    async def get_filing_metadata(self, accession_number: str) -> Optional[FilingMetadata]:
        """
        Retrieves a filing's metadata from DynamoDB.

        :param accession_number: The unique identifier for the filing.
        :return: A FilingMetadata object or None if not found.
        """
        try:
            response = self.table.get_item(Key={'accession_number': accession_number})
            item = response.get('Item')
            if item:
                logger.info(f"Found metadata for {accession_number} in DynamoDB.")
                # Convert dates from string back to datetime if necessary
                item['filing_date'] = datetime.fromisoformat(item['filing_date'])
                item['created_at'] = datetime.fromisoformat(item['created_at'])
                item['updated_at'] = datetime.fromisoformat(item['updated_at'])
                for chunk in item.get('chunks', []):
                    chunk['created_at'] = datetime.fromisoformat(chunk['created_at'])
                return FilingMetadata(**item)
            return None
        except ClientError as e:
            logger.error(f"Error getting metadata for {accession_number}: {e}")
            return None

    async def save_filing_metadata(self, metadata: FilingMetadata):
        """
        Saves or updates a filing's metadata in DynamoDB.

        :param metadata: The FilingMetadata object to save.
        """
        try:
            # Convert datetime objects to ISO 8601 strings for DynamoDB
            item = metadata.model_dump()
            item['filing_date'] = metadata.filing_date.isoformat()
            item['created_at'] = metadata.created_at.isoformat()
            item['updated_at'] = datetime.utcnow().isoformat() # Always update timestamp
            for chunk in item.get('chunks', []):
                chunk['created_at'] = chunk['created_at'].isoformat()

            self.table.put_item(Item=item)
            logger.info(f"Successfully saved metadata for {metadata.accession_number}.")
        except ClientError as e:
            logger.error(f"Error saving metadata for {metadata.accession_number}: {e}")
            raise

# Singleton instance
_db_service: Optional[DynamoDBMetadataService] = None

def get_db_metadata_service() -> DynamoDBMetadataService:
    """
    Provides a singleton instance of the DynamoDBMetadataService.
    """
    global _db_service
    if _db_service is None:
        _db_service = DynamoDBMetadataService()
    return _db_service 