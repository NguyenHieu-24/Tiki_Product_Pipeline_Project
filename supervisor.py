import subprocess
import sys
import time
from pathlib import Path

from config import AUTO_RESTART_DELAY, AUTO_RESTART_MAX, ROOT_DIR
from pipelines.monitor import send_alert, write_status


def main():
    first_run_reset = "--reset" in sys.argv
    restart_count = 0

    while True:
        command = [sys.executable, str(Path(ROOT_DIR) / "main.py")]

        # Important: reset only on the first launch.
        # Subsequent auto-restarts must resume from checkpoint.
        if first_run_reset and restart_count == 0:
            command.append("--reset")
        print(f"[SUPERVISOR] Starting: {' '.join(command)}")
        write_status(
            "Supervisor started main pipeline",
            {"restart_count": restart_count},
        )

        try:
            result = subprocess.run(command, cwd=ROOT_DIR)
        except KeyboardInterrupt:
            send_alert("Supervisor stopped by user.")
            print("\n[SUPERVISOR] Stopped by user.")
            return

        if result.returncode == 0:
            print("[SUPERVISOR] Main pipeline completed successfully.")
            write_status(
                "Supervisor: main pipeline completed successfully",
                {"restart_count": restart_count},
            )
            return

        restart_count += 1
        send_alert(
            "Main pipeline stopped unexpectedly; supervisor will restart it.",
            {
                "return_code": result.returncode,
                "restart_count": restart_count,
            },
        )

        if restart_count > AUTO_RESTART_MAX:
            send_alert(
                "Auto-restart limit reached. Manual inspection is required.",
                {"restart_count": restart_count},
            )
            print("[SUPERVISOR] Auto-restart limit reached.")
            return

        print(
            f"[SUPERVISOR] Main exited with code {result.returncode}. "
            f"Restarting in {AUTO_RESTART_DELAY}s..."
        )
        time.sleep(AUTO_RESTART_DELAY)


if __name__ == "__main__":
    main()
