import argparse
import subprocess
import os
import re
import sys
import tempfile
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: 'python-dotenv' is required.", file=sys.stderr)
    print("Install it with: pip install python-dotenv", file=sys.stderr)
    sys.exit(1)

def run_rclone_sync(remote_path: str, local_dir: Path) -> None:
    """
    Executes the `rclone sync` command as a subprocess to download or update files from Google Drive.
    
    Args:
        remote_path (str): The rclone remote and path (e.g., ':drive,service_account_file=...:docs_for_hackenza').
        local_dir (Path): The local destination directory where files will be saved.
        
    Raises:
        SystemExit: If rclone is not installed or if the sync command fails.
    """
    print(f"Syncing Google Drive ({remote_path}) to {local_dir}...")
    
    # Rclone command tailored for our use case:
    #   sync                     : Makes the destination identical to the source.
    #   --drive-export-formats   : Crucial! Tells Google Drive to export Google Docs/Sheets as docx/xlsx.
    #   --update                 : Skips files that are newer on the local destination.
    #   --use-mmap               : Optimizes memory usage for large file transfers.
    #   --transfers              : Number of concurrent file downloads (4 is a safe default).
    #   --progress               : Shows a live progress bar in the terminal stdout.
    cmd = [
        "rclone", "sync", 
        remote_path, 
        str(local_dir),
        "--drive-export-formats", "docx,xlsx,csv,pdf,txt",
        "--update",
        "--use-mmap",
        "--transfers", "4",
        "--progress"
    ]
    
    try:
        # Run rclone and stream the output to the terminal
        subprocess.run(cmd, check=True)
        print("Sync complete!\n")
    except subprocess.CalledProcessError as e:
        print(f"Error: rclone sync failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'rclone' is not installed or not in PATH.", file=sys.stderr)
        sys.exit(1)

def main() -> None:
    """
    Main entry point for the script.
    Parses CLI arguments, constructs the remote path, and triggers the rclone sync.
    """
    parser = argparse.ArgumentParser(
        description="Syncs a Google Drive folder to a local directory using a Service Account."
    )
    parser.add_argument(
        "drive_link", 
        help="Google Drive link or folder/file ID to sync (e.g. 'https://drive.google.com/drive/folders/abc123' or just 'abc123')."
    )
    parser.add_argument("dest", help="Local destination directory to sync files into.")
    args = parser.parse_args()

    local_root = Path(args.dest).resolve()

    # Load environment variables from .env file
    load_dotenv()
    
    sa_json = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        print("Error: 'GDRIVE_SERVICE_ACCOUNT_JSON' not found in your environment or .env file.", file=sys.stderr)
        print("Please create a .env file and paste your Service Account JSON array into this variable.", file=sys.stderr)
        sys.exit(1)

    # If the user passed a full URL, extract just the ID part using regex
    folder_input = args.drive_link
    match = re.search(r'file/d/([a-zA-Z0-9_-]+)|folders/([a-zA-Z0-9_-]+)|id=([a-zA-Z0-9_-]+)', folder_input)
    if match:
        folder_id = next(g for g in match.groups() if g)
    else:
        # Assume they passed the raw ID directly
        folder_id = folder_input

    # Ensure directories exist
    local_root.mkdir(parents=True, exist_ok=True)

    # Rclone requires the JSON to be passed as a file path. 
    # Since we are reading from .env for security, we write it to a secure, 
    # temporary file just for the duration of the rclone command, then delete it.
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_creds:
        temp_creds.write(sa_json)
        temp_creds_path = temp_creds.name

    try:
        # Construct the on-the-fly rclone remote string.
        # We explicitly DO NOT use `shared_with_me=true` here. When combined with `root_folder_id`, 
        # it causes rclone to hang indefinitely. `root_folder_id` alone grants full access 
        # to the shared folder via the Service Account.
        remote_path = f":drive,service_account_file='{temp_creds_path}',root_folder_id='{folder_id}':"

        # 1. Sync from Drive to Local files
        run_rclone_sync(remote_path, local_root)
        print("All done!")
    finally:
        # Unconditionally clean up the temporary credentials file
        if os.path.exists(temp_creds_path):
            os.remove(temp_creds_path)

if __name__ == "__main__":
    main()
