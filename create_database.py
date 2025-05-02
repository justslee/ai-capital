import psycopg2
import sys

try:
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(
        host="database-1.cj6qsswemdys.us-east-2.rds.amazonaws.com",
        database="postgres",  # Connect to default postgres database first
        user="postgres",
        password="D2i2OufzIJmZWGLxchzJ",
        port="5432"
    )
    
    # Make the connection autocommit
    conn.autocommit = True
    
    # Create a cursor
    cur = conn.cursor()
    
    # Check if database already exists
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'company_data'")
    exists = cur.fetchone()
    
    if not exists:
        # Create the new database
        cur.execute("CREATE DATABASE company_data")
        print("Database 'company_data' created successfully!")
    else:
        print("Database 'company_data' already exists.")
    
    # Close the cursor and connection
    cur.close()
    conn.close()
    
    print("Database setup complete!")
    sys.exit(0)
    
except Exception as e:
    print(f"Error setting up database: {e}")
    sys.exit(1) 