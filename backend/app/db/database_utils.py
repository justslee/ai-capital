import psycopg2
from urllib.parse import urlparse
from app.core.config import DATABASE_URL # Corrected import path
import sys

_conn_params = None
if DATABASE_URL:
    try:
        # Ensure +asyncpg is removed if present, as psycopg2 doesn't use it.
        db_url_for_psycopg2 = DATABASE_URL.replace("+asyncpg", "")
        parsed_url = urlparse(db_url_for_psycopg2)
        _conn_params = {
            'dbname': parsed_url.path[1:],
            'user': parsed_url.username,
            'password': parsed_url.password,
            'host': parsed_url.hostname,
            'port': parsed_url.port or 5432, # Default to 5432 if port not in URL
            'sslmode': 'require' # Assuming SSL is required
        }
    except Exception as e:
        print(f"Error parsing DATABASE_URL ('{DATABASE_URL}'): {e}. DB connections will fail.", file=sys.stderr)
        _conn_params = None
elif not DATABASE_URL:
    print("FATAL: app.db.database_utils cannot initialize connection parameters. DATABASE_URL is not set in app.core.config.", file=sys.stderr)

def get_db_connection():
    """Establishes and returns a new database connection using Psycopg2."""
    if not _conn_params:
        print("Error: Database connection parameters not properly configured. Cannot create connection.", file=sys.stderr)
        raise ConnectionError("Database connection parameters are not configured due to an earlier error or missing DATABASE_URL.")
    
    try:
        conn = psycopg2.connect(**_conn_params)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database with psycopg2: {e}", file=sys.stderr)
        # In a real app, you might want to log this error more formally
        # or have more sophisticated retry/error handling.
        raise # Re-raise the exception to be handled by the caller

# Optional: A context manager for handling connections and cursors cleanly
from contextlib import contextmanager

@contextmanager
def db_cursor(commit_on_exit=False):
    """Provides a database cursor within a context, managing connection and transaction.
    Args:
        commit_on_exit (bool): If True, commits the transaction if no exceptions occur.
                               Otherwise, the caller is responsible for commit/rollback.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        yield cursor
        if commit_on_exit:
            conn.commit()
    except psycopg2.Error as e:
        if conn:
            conn.rollback() # Rollback on database errors
        print(f"Database cursor context error: {e}", file=sys.stderr)
        raise
    except Exception as e:
        if conn:
            conn.rollback() # Rollback on other errors within the try block
        print(f"General cursor context error: {e}", file=sys.stderr)
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close() 