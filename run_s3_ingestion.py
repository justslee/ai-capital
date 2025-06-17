#!/usr/bin/env python3
"""
Quick S3 Ingestion Runner

Convenience script to run S3 bulk ingestion from project root.
"""

import subprocess
import sys
from pathlib import Path

def main():
    # Get the script path
    script_path = Path(__file__).parent / "backend" / "scripts" / "ingestion" / "s3_bulk_ingest.py"
    
    if not script_path.exists():
        print("❌ Error: S3 ingestion script not found!")
        print(f"Expected: {script_path}")
        return 1
    
    print("🚀 Running S3 bulk ingestion...")
    print(f"📄 Script: {script_path}")
    print("-" * 50)
    
    # Run the script
    try:
        result = subprocess.run([sys.executable, str(script_path)], check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running script: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 