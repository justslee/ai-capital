import subprocess
import sys
import os
from dotenv import load_dotenv

def run_price_test(ticker: str):
    """
    Runs the daily price collection test for a given ticker.
    """
    print(f"--- Starting Daily Price Collection Test for {ticker} ---")
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    cli_module = "backend.app.domains.data_collection.cli"
    env_path = os.path.join(project_root, ".env")

    # Explicitly load the .env file
    if os.path.exists(env_path):
        print(f"Loading .env file from: {env_path}")
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        print(f"Warning: .env file not found at {env_path}")
        sys.exit(1)

    try:
        command = [sys.executable, "-m", cli_module, "fetch-daily-prices", ticker]
        
        print(f"Executing command: {' '.join(command)}")
        print(f"Working directory: {project_root}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=project_root
        )

        print("\n--- CLI Output ---")
        print(result.stdout)
        
        if result.stderr:
            print("\n--- CLI Errors ---")
            print(result.stderr)

        if "status': 'success'" in result.stdout or "status': 'up_to_date'" in result.stdout or "status': 'no_new_data'" in result.stdout:
            print(f"\n--- Test Result: SUCCESS ---")
            print(f"Successfully ran daily price collection for {ticker}.")
        else:
            print(f"\n--- Test Result: FAILED ---")
            print(f"The collection process for {ticker} reported failures.")
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
    test_ticker = "AAPL"
    run_price_test(test_ticker) 