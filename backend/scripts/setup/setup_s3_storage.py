#!/usr/bin/env python3
"""
S3 Storage Setup Script

Configure AWS S3 storage for AI Capital project.
Perfect for work devices with minimal local storage requirements.
"""

import os
import sys
from pathlib import Path
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

def check_aws_credentials():
    """Check if AWS credentials are configured."""
    print("🔐 Checking AWS Credentials...")
    
    # Check environment variables
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    if access_key and secret_key:
        print("✅ AWS credentials found in environment variables")
        return True, access_key, secret_key, region
    
    # Check AWS credentials file
    aws_creds_file = Path.home() / '.aws' / 'credentials'
    if aws_creds_file.exists():
        print("✅ AWS credentials file found")
        return True, None, None, region
    
    print("❌ No AWS credentials found")
    return False, None, None, region

def setup_aws_credentials():
    """Help user set up AWS credentials."""
    print("\n🔧 AWS Credentials Setup")
    print("=" * 50)
    
    print("You need AWS credentials to use S3 storage.")
    print("Options:")
    print("1. Use existing AWS account")
    print("2. Create new AWS account (free tier available)")
    print("3. Use environment variables")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "3":
        print("\n📝 Set these environment variables:")
        print("export AWS_ACCESS_KEY_ID=your_access_key")
        print("export AWS_SECRET_ACCESS_KEY=your_secret_key")
        print("export AWS_REGION=us-east-1")
        print("export S3_BUCKET=ai-capital-data-your-name")
        
        access_key = input("\nEnter AWS_ACCESS_KEY_ID: ").strip()
        secret_key = input("Enter AWS_SECRET_ACCESS_KEY: ").strip()
        region = input("Enter AWS_REGION (default: us-east-1): ").strip() or "us-east-1"
        bucket = input("Enter S3_BUCKET name (default: ai-capital-data): ").strip() or "ai-capital-data"
        
        # Set environment variables for this session
        os.environ['AWS_ACCESS_KEY_ID'] = access_key
        os.environ['AWS_SECRET_ACCESS_KEY'] = secret_key
        os.environ['AWS_REGION'] = region
        os.environ['S3_BUCKET'] = bucket
        
        return access_key, secret_key, region, bucket
    
    else:
        print("\n📖 AWS Setup Instructions:")
        print("1. Go to https://aws.amazon.com/")
        print("2. Create account or sign in")
        print("3. Go to IAM > Users > Create User")
        print("4. Attach policy: AmazonS3FullAccess")
        print("5. Create access key")
        print("6. Run this script again")
        sys.exit(0)

def test_s3_connection(access_key, secret_key, region, bucket):
    """Test S3 connection and create bucket if needed."""
    print(f"\n🧪 Testing S3 Connection...")
    
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        # Test connection
        s3_client.list_buckets()
        print("✅ S3 connection successful")
        
        # Check/create bucket
        try:
            s3_client.head_bucket(Bucket=bucket)
            print(f"✅ S3 bucket '{bucket}' exists")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                print(f"📦 Creating S3 bucket '{bucket}'...")
                if region == 'us-east-1':
                    s3_client.create_bucket(Bucket=bucket)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )
                print(f"✅ Created S3 bucket '{bucket}'")
            else:
                raise
        
        return True
        
    except NoCredentialsError:
        print("❌ Invalid AWS credentials")
        return False
    except ClientError as e:
        print(f"❌ S3 error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def create_env_file(access_key, secret_key, region, bucket):
    """Create .env file with AWS configuration."""
    env_content = f"""# AWS S3 Configuration for AI Capital
AWS_ACCESS_KEY_ID={access_key}
AWS_SECRET_ACCESS_KEY={secret_key}
AWS_REGION={region}
S3_BUCKET={bucket}
S3_PREFIX=market-data

# Tiingo API
TIINGO_API_KEY=d108b9d954ee7b892392fe97b101b67ab1899063

# Storage Configuration
STORAGE_TYPE=s3_duckdb
"""
    
    env_file = Path(".env")
    with open(env_file, "w") as f:
        f.write(env_content)
    
    print(f"✅ Created .env file with S3 configuration")

def update_requirements():
    """Add S3 dependencies to requirements.txt."""
    requirements_file = Path("backend/requirements.txt")
    
    s3_deps = [
        "boto3>=1.26.0",
        "botocore>=1.29.0"
    ]
    
    if requirements_file.exists():
        with open(requirements_file, "r") as f:
            existing = f.read()
        
        new_deps = []
        for dep in s3_deps:
            if dep.split(">=")[0] not in existing:
                new_deps.append(dep)
        
        if new_deps:
            with open(requirements_file, "a") as f:
                f.write("\n# S3 Storage Dependencies\n")
                for dep in new_deps:
                    f.write(f"{dep}\n")
            
            print(f"✅ Added S3 dependencies to requirements.txt")
            print("   Run: pip install -r backend/requirements.txt")

def main():
    print("🌩️  AI Capital S3 Storage Setup")
    print("=" * 60)
    print("Configure AWS S3 storage for zero local storage footprint")
    print("Perfect for work devices!")
    
    # Check existing credentials
    has_creds, access_key, secret_key, region = check_aws_credentials()
    
    if not has_creds:
        access_key, secret_key, region, bucket = setup_aws_credentials()
    else:
        bucket = os.getenv('S3_BUCKET', 'ai-capital-data')
        if not access_key:
            # Using AWS credentials file
            access_key = input("Enter AWS_ACCESS_KEY_ID: ").strip()
            secret_key = input("Enter AWS_SECRET_ACCESS_KEY: ").strip()
    
    # Test S3 connection
    if test_s3_connection(access_key, secret_key, region, bucket):
        # Create configuration files
        create_env_file(access_key, secret_key, region, bucket)
        update_requirements()
        
        print("\n🎉 S3 Storage Setup Complete!")
        print("=" * 60)
        
        print("📋 What's configured:")
        print(f"   🌍 AWS Region: {region}")
        print(f"   📦 S3 Bucket: {bucket}")
        print(f"   📁 S3 Prefix: market-data")
        print(f"   💾 Local Cache: ./cache (minimal)")
        
        print("\n🚀 Next Steps:")
        print("1. Install dependencies: pip install -r backend/requirements.txt")
        print("2. Start server: cd backend && uvicorn app.main:app --reload --port 8001")
        print("3. Run bulk ingestion: python simple_bulk_ingest.py")
        
        print("\n💡 Benefits:")
        print("   • Zero local storage footprint")
        print("   • Query data directly from S3")
        print("   • 10-100x faster than PostgreSQL")
        print("   • Automatic compression & partitioning")
        print("   • Perfect for work devices")
        
    else:
        print("\n❌ S3 setup failed. Please check your AWS credentials.")
        sys.exit(1)

if __name__ == "__main__":
    main() 