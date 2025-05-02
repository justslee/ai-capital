import psycopg2
import sys

# Try different connection scenarios
connection_params = [
    {
        "host": "database-1.cj6qsswemdys.us-east-2.rds.amazonaws.com",
        "database": "postgres",  # Default postgres database
        "user": "postgres",      # Default postgres admin user
        "password": "D2i2OufzIJmZWGLxchzJ", 
        "port": "5432",
        "sslmode": "require"
    },
    {
        "host": "database-1.cj6qsswemdys.us-east-2.rds.amazonaws.com",
        "database": "postgres",  # Default postgres database
        "user": "admin",         # Try "admin" user (common RDS default)
        "password": "D2i2OufzIJmZWGLxchzJ",
        "port": "5432",
        "sslmode": "require"
    }
]

# Try each connection
for i, params in enumerate(connection_params):
    print(f"\nAttempt {i+1}: Connecting with parameters: {params}")
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(**params)
        
        # Create a cursor
        cur = conn.cursor()
        
        # Execute a simple query
        cur.execute("SELECT version();")
        
        # List databases
        cur.execute("SELECT datname FROM pg_database;")
        databases = cur.fetchall()
        print("Available databases:")
        for db in databases:
            print(f" - {db[0]}")
        
        # Fetch and print the result
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"PostgreSQL database version: {version}")
        
        # Close the cursor and connection
        cur.close()
        conn.close()
        
        print("Database connection test successful!")
        sys.exit(0)
        
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")

print("\nAll connection attempts failed. Please check your RDS settings and credentials.")
sys.exit(1) 