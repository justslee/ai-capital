import subprocess
import sys
import os
from dotenv import load_dotenv

def run_test():
    """
    Runs the comprehensive macro data collection test.
    This test invokes the CLI command to fetch all key FRED indicators.
    """
    print("--- Starting Macro Data Collection Test ---")
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    cli_module = "backend.app.domains.data_collection.cli"
    env_path = os.path.join(project_root, ".env")

    # Explicitly load the .env file
    if os.path.exists(env_path):
        print(f"Loading .env file from: {env_path}")
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        print(f"Warning: .env file not found at {env_path}")


    try:
        command = [sys.executable, "-m", cli_module, "fetch-key-indicators"]
        
        print(f"Executing command: {' '.join(command)}")
        print(f"Working directory: {project_root}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=project_root  # Run from the project root
        )

        print("\n--- CLI Output ---")
        print(result.stdout)
        
        if result.stderr:
            print("\n--- CLI Errors ---")
            print(result.stderr)

        if "failed_collections': 0" in result.stdout and "status': 'completed'" in result.stdout:
            print("\n--- Test Result: SUCCESS ---")
            print("Successfully collected all key macro indicators without any failures.")
        else:
            print("\n--- Test Result: FAILED ---")
            print("The collection process reported failures or did not complete successfully.")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print("\n--- Test Result: FAILED ---")
        print("The CLI command failed with a non-zero exit code.")
        print(f"Return Code: {e.returncode}")
        print("\n--- STDOUT ---")
        print(e.stdout)
        print("\n--- STDERR ---")
        print(e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n--- An unexpected error occurred: {e} ---")
        sys.exit(1)

if __name__ == "__main__":
    run_test() 