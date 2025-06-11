import psycopg2
from contextlib import contextmanager
from app.config import settings

@contextmanager
def db_cursor():
    """Provide a database cursor with automatic connection management."""
    connection = None
    cursor = None
    try:
        # Use psycopg2 format (not asyncpg format) for the URL
        db_url = settings.database_url.replace('+asyncpg', '')
        connection = psycopg2.connect(db_url)
        cursor = connection.cursor()
        yield cursor
        connection.commit()  # Commit if no exceptions
    except Exception as e:
        if connection:
            connection.rollback()  # Rollback on any exception
        raise  # Re-raise the exception
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close() 