import argparse
import subprocess
import sys
from pathlib import Path

def run_rclone_sync(remote_path: str, local_dir: Path) -> None:
    """
    Executes the `rclone sync` command as a subprocess to download or update files from Google Drive.
    
    Args:
        remote_path (str): The rclone remote and path (e.g., 'acad_material:docs_for_hackenza').
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
        description="Syncs a Google Drive folder to a local directory using a pre-configured rclone remote."
    )
    parser.add_argument(
        "gdrive_folder", 
        help="The Google Drive folder name to sync (e.g., 'docs_for_hackenza' or '/' for the entire drive root)."
    )
    parser.add_argument("local_root", help="Local directory to sync Google Drive files into")
    args = parser.parse_args()

    local_root = Path(args.local_root).resolve()

    # The rclone remote name is hardcoded here based on the user's initial setup.
    # Rclone syntax requires the format `remote_name:path/to/folder`.
    # Therefore, if the remote is 'acad_material' and the folder is 'docs_for_hackenza',
    # the remote_path becomes 'acad_material:docs_for_hackenza'.
    remote_path = f"acad_material:{args.gdrive_folder}"
    
    # If the user asks for the drive root using standard root indicators (/, ., etc.),
    # we just pass the remote name with a trailing colon.
    if args.gdrive_folder in ["/", "", "."]:
        remote_path = "acad_material:"

    # Ensure directories exist
    local_root.mkdir(parents=True, exist_ok=True)

    # 1. Sync from Drive to Local files
    run_rclone_sync(remote_path, local_root)
    print("All done!")

if __name__ == "__main__":
    main()
