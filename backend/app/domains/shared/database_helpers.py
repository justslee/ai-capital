"""
Shared Database Helpers

Common database utilities and connection patterns used across domains.
"""

# Standard library imports
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from urllib.parse import urlparse

# Third-party imports
import psycopg2
from sqlalchemy.ext.asyncio import AsyncSession

# App imports
from app.config import settings

logger = logging.getLogger(__name__)


def get_db_connection_params(database_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse database URL and return connection parameters.
    
    Args:
        database_url: Database URL (defaults to settings.database_url)
        
    Returns:
        Dictionary of connection parameters
    """
    url = database_url or settings.database_url
    
    if not url:
        raise ValueError("Database URL is required")
    
    # Remove async driver prefix for psycopg2 compatibility
    parsed_url = urlparse(url.replace("+asyncpg", ""))
    
    return {
        'dbname': parsed_url.path[1:],  # Remove leading slash
        'user': parsed_url.username,
        'password': parsed_url.password,
        'host': parsed_url.hostname,
        'port': parsed_url.port,
        'sslmode': 'require'
    }


@asynccontextmanager
async def safe_db_operation(db: AsyncSession, operation_name: str = "database operation"):
    """
    Safely execute database operations with proper error handling and rollback.
    
    Args:
        db: Database session
        operation_name: Name of the operation for logging
        
    Yields:
        Database session for operations
    """
    try:
        logger.debug(f"Starting {operation_name}")
        yield db
        await db.commit()
        logger.debug(f"Successfully completed {operation_name}")
        
    except Exception as e:
        logger.error(f"Error in {operation_name}: {e}")
        await db.rollback()
        raise
        

def create_sync_db_connection(database_url: Optional[str] = None) -> psycopg2.extensions.connection:
    """
    Create synchronous database connection for legacy operations.
    
    Args:
        database_url: Database URL (defaults to settings.database_url)
        
    Returns:
        psycopg2 connection object
    """
    conn_params = get_db_connection_params(database_url)
    return psycopg2.connect(**conn_params)


def format_sql_in_clause(values: list) -> str:
    """
    Safely format values for SQL IN clause.
    
    Args:
        values: List of values to include in IN clause
        
    Returns:
        Formatted string for SQL IN clause
    """
    if not values:
        return "NULL"
    
    # Escape single quotes and wrap in quotes
    escaped_values = [f"'{str(v).replace(chr(39), chr(39) + chr(39))}'" for v in values]
    return f"({', '.join(escaped_values)})"


def batch_process_records(records: list, batch_size: int = 1000):
    """
    Generator to process records in batches.
    
    Args:
        records: List of records to process
        batch_size: Size of each batch
        
    Yields:
        Batches of records
    """
    for i in range(0, len(records), batch_size):
        yield records[i:i + batch_size]


def validate_database_connection(database_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Test database connection and return status.
    
    Args:
        database_url: Database URL to test
        
    Returns:
        Dictionary with connection status
    """
    result = {
        "connected": False,
        "error": None,
        "database_info": {}
    }
    
    try:
        conn_params = get_db_connection_params(database_url)
        
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                # Test basic connectivity
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                
                cur.execute("SELECT current_database()")
                db_name = cur.fetchone()[0]
                
                result["connected"] = True
                result["database_info"] = {
                    "version": version,
                    "database": db_name,
                    "host": conn_params["host"],
                    "port": conn_params["port"]
                }
                
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Database connection test failed: {e}")
    
    return result 