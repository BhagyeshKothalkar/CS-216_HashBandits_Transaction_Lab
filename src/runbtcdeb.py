import os
import sys

import pexpect


def run_btcdeb_steps(raw_tx_hex, prev_tx_hex):

    command = f"btcdeb -v --tx={raw_tx_hex} --txin={prev_tx_hex}"
    print(f"Spawning process: {command}\n")

    try:
        custom_env = os.environ.copy()
        custom_env["TERM"] = "dumb"
        # Force strict terminal boundaries so btcdeb's UI renderer doesn't segfault
        custom_env["COLUMNS"] = "100"
        custom_env["LINES"] = "40"

        # Explicitly allocate the PTY dimensions in pexpect
        child = pexpect.spawn(
            command, encoding="utf-8", timeout=5, env=custom_env, dimensions=(40, 100)
        )

        child.logfile_read = sys.stdout
        prompt = r"btcdeb>"

        child.expect([prompt, r">", pexpect.TIMEOUT], timeout=2)
        print("\n--- Initial btcdeb State loaded successfully ---")

        step_count = 0
        while True:
            step_count += 1
            print(f"\n--- Executing Step {step_count} ---")

            child.sendline("step")

            match_index = child.expect([prompt, r"at end of script", r"error"])

            if match_index == 1:
                print(
                    "\n\n[✓] Script execution finished successfully (Reached end of script)."
                )
                break
            elif match_index == 2:
                print("\n\n[x] Script execution encountered an error.")
                break

            output_lower = child.before.lower()
            if "script failed" in output_lower:
                print("\n\n[x] Script execution failed.")
                break

    except pexpect.EOF:
        print("\n\n[-] btcdeb process exited unexpectedly (EOF).")
        child.close()
        print(f"Exit Status: {child.exitstatus}")
        print(f"Signal Status: {child.signalstatus} (If 11, it is a Segfault)")
        print("--- Output before crash ---")
        print(child.before)
    except pexpect.TIMEOUT:
        print("\n\n[-] Timed out waiting for btcdeb.")
        print("--- Output before timeout ---")
        print(child.before)
    finally:
        if "child" in locals() and child.isalive():
            child.sendline("quit")
            child.close()
            print("btcdeb process closed.")


if __name__ == "__main__":
    run_btcdeb_steps()
