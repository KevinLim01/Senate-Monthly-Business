from __future__ import annotations

import itertools
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime


def timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(message: str) -> None:
    print(f"[{timestamp()}] {message}", flush=True)


@contextmanager
def ticker(message: str, enabled: bool = True):
    """Small terminal spinner for slow steps like Gemini review.

    Keeps printing while the wrapped block is running, so the user can tell the
    script has not frozen.
    """
    if not enabled:
        yield
        return

    stop = threading.Event()
    frames = itertools.cycle(["|", "/", "-", "\\"])

    def run_spinner() -> None:
        while not stop.is_set():
            frame = next(frames)
            sys.stdout.write(f"\r[{timestamp()}] {message} {frame}")
            sys.stdout.flush()
            time.sleep(0.15)
        sys.stdout.write("\r" + " " * (len(message) + 30) + "\r")
        sys.stdout.flush()

    thread = threading.Thread(target=run_spinner, daemon=True)
    thread.start()
    start = time.time()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=1)
        elapsed = time.time() - start
        log(f"Done: {message} ({elapsed:.1f}s)")
