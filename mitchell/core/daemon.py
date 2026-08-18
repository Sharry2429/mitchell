import os
import sys
import time
import subprocess
import urllib.request
import urllib.error
import logging

logger = logging.getLogger("mitchell.core.daemon")

def is_api_running(port: int = 7000) -> bool:
    url = f"http://localhost:{port}/v1/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=1.0) as response:
            return response.status == 200
    except Exception:
        return False

def ensure_api_running(port: int = 7000):
    if is_api_running(port):
        logger.debug(f"Mitchell API is already running on port {port}.")
        return

    logger.info(f"Starting Mitchell API background service on port {port}...")
    
    # Spawn the background service
    # We use sys.executable -m mitchell.api
    cmd = [sys.executable, "-m", "mitchell.api"]
    
    # Use CREATE_NO_WINDOW on Windows to prevent a console pop-up
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW

    env = os.environ.copy()
    env["MITCHELL_API_PORT"] = str(port)

    subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True
    )

    # Wait for the API to become ready (up to 5 seconds)
    for i in range(50):
        time.sleep(0.1)
        if is_api_running(port):
            logger.info("Mitchell API is up and running.")
            return

    logger.warning("Mitchell API started but did not respond to health check within 5 seconds.")
