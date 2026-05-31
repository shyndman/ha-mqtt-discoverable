#!/usr/bin/env -S uv run
from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
MOSQUITTO_CONFIG: Final[Path] = REPO_ROOT / "tests" / "mosquitto.conf"
MQTT_HOST: Final[str] = "127.0.0.1"
MQTT_PORT: Final[int] = 1883
BROKER_STARTUP_TIMEOUT_SECONDS: Final[float] = 5.0
BROKER_SHUTDOWN_TIMEOUT_SECONDS: Final[float] = 5.0
TEST_TIMEOUT_SECONDS: Final[float] = 120.0


def print_status(message: str) -> None:
    print(f"[INFO] {message}", flush=True)


def print_error(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr, flush=True)


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.1)
        return sock.connect_ex((host, port)) == 0


def start_broker() -> tuple[subprocess.Popen[bytes], Path]:
    log_file = tempfile.NamedTemporaryFile(
        mode="wb",
        prefix="hmd-mosquitto-",
        suffix=".log",
        delete=False,
    )
    log_path = Path(log_file.name)
    process = subprocess.Popen(
        ["mosquitto", "-c", str(MOSQUITTO_CONFIG)],
        stdin=subprocess.DEVNULL,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log_file.close()

    deadline = time.monotonic() + BROKER_STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if is_port_open(MQTT_HOST, MQTT_PORT):
            return process, log_path
        if process.poll() is not None:
            break
        time.sleep(0.1)

    return_code = process.poll()
    if return_code is None:
        process.terminate()
        try:
            _ = process.wait(timeout=BROKER_SHUTDOWN_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            _ = process.wait(timeout=BROKER_SHUTDOWN_TIMEOUT_SECONDS)

    raise RuntimeError(
        f"Mosquitto did not become ready on port {MQTT_PORT}. Log: {log_path}"
    )


def stop_broker(process: subprocess.Popen[bytes], log_path: Path) -> None:
    if process.poll() is None:
        print_status(f"Stopping mosquitto (PID: {process.pid})...")
        process.terminate()
        try:
            _ = process.wait(timeout=BROKER_SHUTDOWN_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            _ = process.wait(timeout=BROKER_SHUTDOWN_TIMEOUT_SECONDS)
        print_status("Mosquitto stopped")

    if log_path.exists():
        log_path.unlink()


def run_pytest(args: list[str]) -> int:
    command = ["uv", "run", "pytest", "-q", *args]
    try:
        completed_process = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
            timeout=TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        print_error(f"Tests timed out after {int(TEST_TIMEOUT_SECONDS)}s")
        return 1

    return completed_process.returncode


def main(args: list[str]) -> int:
    if shutil.which("mosquitto") is None:
        print_error("mosquitto command not found. Please install mosquitto broker.")
        print_error("  Ubuntu/Debian: sudo apt-get install mosquitto")
        print_error("  macOS: brew install mosquitto")
        print_error(
            "  Other: Check your package manager or visit https://mosquitto.org/"
        )
        return 1

    if not MOSQUITTO_CONFIG.is_file():
        print_error(f"Mosquitto config file not found: {MOSQUITTO_CONFIG}")
        return 1

    if is_port_open(MQTT_HOST, MQTT_PORT):
        print_error(
            f"Port {MQTT_PORT} is already in use. Please stop any running MQTT brokers."
        )
        return 1

    print_status("Starting mosquitto MQTT broker...")
    print_status(f"Config: {MOSQUITTO_CONFIG.relative_to(REPO_ROOT)}")
    print_status(f"Port: {MQTT_PORT}")

    try:
        process, log_path = start_broker()
    except RuntimeError as error:
        print_error(str(error))
        return 1

    print_status(f"Mosquitto started with PID: {process.pid}")
    print_status("Running tests...")
    print_status(f"Test timeout: {int(TEST_TIMEOUT_SECONDS)}s")

    try:
        test_exit_code = run_pytest(args)
    finally:
        stop_broker(process, log_path)

    if test_exit_code == 0:
        print_status("All tests passed! ✅")
        print_status("Test run completed successfully")
        return 0

    print_error(f"Tests failed with exit code: {test_exit_code}")
    return test_exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
