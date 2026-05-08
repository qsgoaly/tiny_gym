import argparse
import subprocess
import sys
import time

import requests

SGLANG_URL = "http://localhost:30000"
MODEL_PATH = "Qwen/Qwen3.5-9B"


def wait_for_server(timeout=300):
    print(f"Waiting for sglang server (up to {timeout}s) ...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{SGLANG_URL}/health_generate", timeout=5)
            if r.status_code == 200:
                print("Server is ready!")
                return
        except requests.RequestException:
            pass
        time.sleep(5)
    raise TimeoutError("sglang server did not become ready in time")


def start_server():
    cmd = [
        sys.executable, "-m", "sglang.launch_server",
        "--model-path", MODEL_PATH,
        "--tool-call-parser", "qwen3_coder",
        "--reasoning-parser", "qwen3",
        "--host", "0.0.0.0",
        "--port", "30000",
        "--trust-remote-code",
    ]
    print(f"Launching sglang server: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
    wait_for_server()
    return proc


def main():
    parser = argparse.ArgumentParser(
        description="Bank customer service call simulation"
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        default="cooperative",
        choices=["cooperative", "reluctant", "piecemeal", "wrong_info"],
        help="Which scenario to run (default: cooperative)",
    )
    parser.add_argument(
        "--all", action="store_true", help="Run all scenarios"
    )
    args = parser.parse_args()

    server_proc = None
    try:
        try:
            requests.get(f"{SGLANG_URL}/health_generate", timeout=2)
            print("sglang server already running.")
        except requests.RequestException:
            server_proc = start_server()

        from workflow import run_conversation
        if args.all:
            from workflow import SCENARIOS
            for name in SCENARIOS:
                run_conversation(name)
        else:
            run_conversation(args.scenario)
    finally:
        if server_proc is not None:
            print("\nShutting down sglang server ...")
            server_proc.terminate()
            server_proc.wait(timeout=15)


if __name__ == "__main__":
    main()
