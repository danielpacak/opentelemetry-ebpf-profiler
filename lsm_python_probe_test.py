#!/usr/bin/env python3
"""Trigger the LSM file_open hook from a deep, recognizable Python call stack.

Run this while the profiler is attached with `-probe-link lsm:file_open` and the
Python tracer enabled (it is part of the default `-t all`). Every iteration opens
a file from inside the nested functions below, so a working mixed unwind should
show these Python frame names sitting on top of the kernel openat/LSM frames:

    lsm_probe_open  ->  level_three  ->  level_two  ->  level_one  ->  main
"""

import os
import sys
import time

# A file that is guaranteed to exist and be cheap to open repeatedly.
TARGET_FILE = "/etc/hostname"

# Seconds between opens. Small enough to sample quickly, large enough to avoid
# pinning a core at 100%.
INTERVAL_S = 0.05


def lsm_probe_open(path: str) -> int:
    """Innermost frame: performs the actual open() that fires file_open."""
    fd = os.open(path, os.O_RDONLY)
    try:
        os.read(fd, 64)
    finally:
        os.close(fd)
    return fd


def level_three(path: str) -> None:
    lsm_probe_open(path)


def level_two(path: str) -> None:
    level_three(path)


def level_one(path: str) -> None:
    level_two(path)


def main() -> None:
    print(f"pid={os.getpid()} opening {TARGET_FILE} every {INTERVAL_S}s")
    print("expected python frames (top->bottom): "
          "lsm_probe_open -> level_three -> level_two -> level_one -> main")
    print("press Ctrl+C to stop")
    count = 0
    try:
        while True:
            level_one(TARGET_FILE)
            count += 1
            if count % 100 == 0:
                print(f"opened {count} times", flush=True)
            time.sleep(INTERVAL_S)
    except KeyboardInterrupt:
        print(f"\nstopped after {count} opens")
        sys.exit(0)


if __name__ == "__main__":
    main()
