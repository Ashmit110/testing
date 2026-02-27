"""
run_pipeline.py
---------------
Periodically runs the two-step Google Drive ingestion pipeline:
  1. sync_from_drive.py  — pulls new/changed files from Google Drive
  2. convert_to_txt.py   — converts them to .txt for RAG/LLM ingestion

Usage
-----
    python run_pipeline.py <drive_link> <raw_dir> <text_dir> [options]

Options
-------
    --interval SECONDS      How often to run the pipeline (default: 3600 = 1 hour)
    --force                 Pass --force to convert_to_txt.py (reprocess all files every run)
    --once                  Run exactly once and exit (no loop)
    --scripts-dir DIR       Directory containing the two pipeline scripts
                            (default: same directory as this file)
    --trigger-file PATH     Path to the trigger file watched for on-demand runs
                            (default: pipeline.trigger, next to this script)

External Trigger (on-demand execution)
---------------------------------------
Any external process can force an immediate pipeline run at any time — even
mid-sleep — by creating the trigger file (default: pipeline.trigger):

    # Trigger a normal run
    touch pipeline.trigger

    # Trigger a --force run (reprocess all files)
    echo "force" > pipeline.trigger

The scheduler wakes up, detects the file, consumes it (deletes it), and
immediately runs the pipeline. The contents of the file control behaviour:
  - empty / anything other than "force" → normal run
  - "force"                              → run with --force flag

After a triggered run the full scheduled interval resets, so a trigger never
shortens the next regular window.

Examples
--------
    # Run every hour (default)
    python run_pipeline.py "https://drive.google.com/drive/folders/ABC" ./raw ./txt

    # Run every 30 minutes
    python run_pipeline.py "https://drive.google.com/drive/folders/ABC" ./raw ./txt --interval 1800

    # Use a custom trigger file path
    python run_pipeline.py "https://drive.google.com/drive/folders/ABC" ./raw ./txt --trigger-file /tmp/my.trigger

    # Run once and exit (no loop, no trigger watching)
    python run_pipeline.py "https://drive.google.com/drive/folders/ABC" ./raw ./txt --once
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TRIGGER_POLL_INTERVAL = 2  # seconds between trigger-file checks during sleep


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run_step(label: str, cmd: list[str]) -> bool:
    """Run a subprocess step, stream its output, and return True on success."""
    log(f"▶ Starting: {label}")
    log(f"  Command : {' '.join(cmd)}")
    print(flush=True)

    result = subprocess.run(cmd)

    print(flush=True)
    if result.returncode == 0:
        log(f"✓ Finished: {label}")
        return True
    else:
        log(f"✗ FAILED  : {label}  (exit code {result.returncode})")
        return False


def run_pipeline(
    drive_link: str,
    raw_dir: str,
    text_dir: str,
    scripts_dir: Path,
    force: bool,
) -> None:
    """Execute sync → convert in order."""
    sep = "─" * 60
    log(sep)
    log(f"Pipeline run started  {'[--force]' if force else ''}")
    log(sep)

    python = sys.executable

    # Step 1 — Sync from Google Drive
    sync_script = scripts_dir / "sync_from_drive.py"
    step1_ok = run_step(
        "Step 1/2 — sync_from_drive.py",
        [python, str(sync_script), drive_link, raw_dir],
    )

    if not step1_ok:
        log("⚠ Skipping Step 2 because Step 1 failed.")
        log(sep)
        return

    # Step 2 — Convert to TXT
    convert_script = scripts_dir / "convert_to_txt.py"
    convert_cmd = [python, str(convert_script), raw_dir, text_dir]
    if force:
        convert_cmd.append("--force")

    run_step("Step 2/2 — convert_to_txt.py", convert_cmd)

    log(sep)
    log("Pipeline run complete")
    log(sep)


# ---------------------------------------------------------------------------
# Trigger-aware sleep
# ---------------------------------------------------------------------------

def interruptible_sleep(
    seconds: int,
    trigger_file: Path,
) -> tuple[bool, bool]:
    """
    Sleep for `seconds`, but poll for the trigger file every
    TRIGGER_POLL_INTERVAL seconds so we can wake up early.

    Returns:
        (triggered, force_flag)
        triggered  — True if a trigger file woke us up early
        force_flag — True if the trigger file contained "force"
    """
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            time.sleep(TRIGGER_POLL_INTERVAL)
        except KeyboardInterrupt:
            raise

        if trigger_file.exists():
            # Read and immediately consume (delete) the trigger file
            try:
                content = trigger_file.read_text(encoding="utf-8").strip().lower()
                trigger_file.unlink()
            except OSError:
                # Race condition: another process deleted it first — ignore
                continue

            force_flag = (content == "force")
            log(
                f"🔔 Trigger file detected! "
                f"({'--force run' if force_flag else 'normal run'})"
            )
            return True, force_flag

    return False, False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Periodically runs sync_from_drive.py then convert_to_txt.py, "
                    "with support for on-demand triggering via a trigger file."
    )
    parser.add_argument("drive_link", help="Google Drive folder URL or ID")
    parser.add_argument("raw_dir",   help="Local directory for downloaded raw files")
    parser.add_argument("text_dir",  help="Output directory for converted .txt files")
    parser.add_argument(
        "--interval", type=int, default=3600, metavar="SECONDS",
        help="Seconds between scheduled pipeline runs (default: 3600 = 1 hour)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Always pass --force to convert_to_txt.py on every scheduled run",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Run the pipeline exactly once and exit (trigger file is ignored)",
    )
    parser.add_argument(
        "--scripts-dir", default=None, metavar="DIR",
        help="Directory containing sync_from_drive.py and convert_to_txt.py "
             "(default: same directory as this script)",
    )
    parser.add_argument(
        "--trigger-file", default=None, metavar="PATH",
        help="Path to the trigger file for on-demand runs "
             "(default: pipeline.trigger next to this script). "
             "Create this file to trigger an immediate run; "
             "write 'force' into it to trigger a --force run.",
    )
    args = parser.parse_args()

    scripts_dir = (
        Path(args.scripts_dir).resolve()
        if args.scripts_dir
        else Path(__file__).parent.resolve()
    )
    trigger_file = (
        Path(args.trigger_file).resolve()
        if args.trigger_file
        else Path(__file__).parent.resolve() / "pipeline.trigger"
    )

    # Validate that both pipeline scripts exist
    for name in ("sync_from_drive.py", "convert_to_txt.py"):
        script = scripts_dir / name
        if not script.exists():
            print(
                f"Error: '{script}' not found. "
                "Use --scripts-dir to specify its location.",
                file=sys.stderr,
            )
            sys.exit(1)

    # --once: single run, no loop, no trigger watching
    if args.once:
        run_pipeline(args.drive_link, args.raw_dir, args.text_dir, scripts_dir, args.force)
        return

    log("Scheduler started")
    log(f"  Interval     : {args.interval}s ({args.interval / 60:.1f} min)")
    log(f"  Trigger file : {trigger_file}")
    log(f"  Force mode   : {'always' if args.force else 'only when trigger file contains \"force\"'}")
    log("Press Ctrl+C to stop.\n")

    # Clear any stale trigger file left from a previous run
    if trigger_file.exists():
        trigger_file.unlink()
        log(f"⚠ Stale trigger file removed: {trigger_file}\n")

    run_number = 0
    while True:
        # ── Scheduled run ──────────────────────────────────────────────────
        run_number += 1
        log(f"=== Scheduled Run #{run_number} ===")
        run_pipeline(
            args.drive_link, args.raw_dir, args.text_dir, scripts_dir, args.force
        )

        log(
            f"Sleeping for {args.interval}s "
            f"({args.interval // 60}m {args.interval % 60}s). "
            f"Create '{trigger_file.name}' to run immediately "
            f"(write 'force' inside for a --force run).\n"
        )

        # ── Trigger-aware sleep ─────────────────────────────────────────────
        try:
            triggered, trigger_force = interruptible_sleep(args.interval, trigger_file)
        except KeyboardInterrupt:
            log("Interrupted by user. Exiting.")
            sys.exit(0)

        # ── Triggered run (if woken early) ──────────────────────────────────
        if triggered:
            run_number += 1
            log(f"=== Triggered Run #{run_number} ===")
            run_pipeline(
                args.drive_link,
                args.raw_dir,
                args.text_dir,
                scripts_dir,
                force=args.force or trigger_force,  # honour both sources of --force
            )
            log("Resuming normal schedule — full interval reset.\n")
            # Loop back to the top: next sleep will be a full `--interval` window.


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
        sys.exit(0)
