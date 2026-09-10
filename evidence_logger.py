"""
Evidence Logger for Kitchen Agent

This file does NOT modify the Kitchen Agent.
It launches the existing voice agent and records its real terminal output.

Usage:
    python evidence_logger.py test1
    python evidence_logger.py test2
    python evidence_logger.py test3
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = PROJECT_DIR / "evidence"

AGENT_COMMAND = [
    sys.executable,
    "-m",
    "voice.voice_shell",
    "dev",
]


# ---------------------------------------------------------
# Test names
# ---------------------------------------------------------

TEST_FILES = {
    "test1": "test1_normal.log",
    "test2": "test2_interruption.log",
    "test3": "test3_stress.log",
}


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    if len(sys.argv) != 2 or sys.argv[1].lower() not in TEST_FILES:
        print()
        print("Usage:")
        print("  python evidence_logger.py test1")
        print("  python evidence_logger.py test2")
        print("  python evidence_logger.py test3")
        print()
        return

    test_name = sys.argv[1].lower()

    EVIDENCE_DIR.mkdir(exist_ok=True)

    log_file = EVIDENCE_DIR / TEST_FILES[test_name]

    start_time = datetime.now()

    print("=" * 70)
    print("KITCHEN AGENT — AUTOMATIC EVIDENCE LOGGER")
    print("=" * 70)
    print(f"Test       : {test_name}")
    print(f"Started    : {start_time.isoformat(timespec='seconds')}")
    print(f"Log file   : {log_file}")
    print()
    print("Starting the REAL Kitchen Agent...")
    print("Everything printed by the agent will be saved.")
    print()
    print("Press Ctrl+C when you want to stop the test.")
    print("=" * 70)
    print()

    # -----------------------------------------------------
    # Open evidence file
    # -----------------------------------------------------

    with open(
        log_file,
        "w",
        encoding="utf-8",
        errors="replace"
    ) as log:

        # Evidence header
        log.write("=" * 70 + "\n")
        log.write("KITCHEN AGENT — TEST EVIDENCE\n")
        log.write("=" * 70 + "\n")
        log.write(f"Test: {test_name}\n")
        log.write(
            f"Started: {start_time.isoformat(timespec='seconds')}\n"
        )
        log.write("Command: python -m voice.voice_shell dev\n")
        log.write("=" * 70 + "\n\n")

        log.flush()

        process = None

        try:

            # -------------------------------------------------
            # Start the EXISTING voice agent
            # -------------------------------------------------

            process = subprocess.Popen(
                AGENT_COMMAND,
                cwd=PROJECT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=None,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            # -------------------------------------------------
            # Capture real terminal output
            # -------------------------------------------------

            for line in process.stdout:

                # Show exactly what the agent printed
                print(line, end="")

                # Save exactly what the agent printed
                log.write(line)
                log.flush()

        except KeyboardInterrupt:

            print()
            print()
            print("=" * 70)
            print("Stopping test...")
            print("=" * 70)

            log.write("\n")
            log.write("=" * 70 + "\n")
            log.write("TEST STOPPED BY USER\n")
            log.write("=" * 70 + "\n")

            if process is not None:
                process.terminate()

                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

        except Exception as e:

            print()
            print("ERROR:", e)

            log.write("\n")
            log.write("=" * 70 + "\n")
            log.write("LOGGER ERROR\n")
            log.write("=" * 70 + "\n")
            log.write(str(e) + "\n")

        finally:

            end_time = datetime.now()

            log.write("\n")
            log.write("=" * 70 + "\n")
            log.write("EVIDENCE SESSION ENDED\n")
            log.write("=" * 70 + "\n")
            log.write(
                f"Ended: {end_time.isoformat(timespec='seconds')}\n"
            )

    print()
    print("=" * 70)
    print("EVIDENCE SAVED")
    print("=" * 70)
    print(f"File: {log_file}")
    print()
    print("The existing Kitchen Agent files were NOT modified.")
    print("=" * 70)


if __name__ == "__main__":
    main()