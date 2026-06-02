#!/usr/bin/env python3
"""Trigger the LSM task_alloc hook from a deep, recognizable Python call stack.

Run this while the profiler is attached with `-probe-link lsm:task_alloc` and the
Python tracer enabled (it is part of the default `-t all`). The task_alloc hook
fires inside copy_process() while a new task is being created, in the context of
the *parent* doing the fork. Every iteration forks a short-lived child from
inside the nested functions below, so a working mixed unwind should show these
Python frame names (the parent's stack) sitting on top of the kernel
clone/copy_process/task_alloc frames:

    lsm_probe_fork  ->  level_three  ->  level_two  ->  level_one  ->  main
"""

import os
import sys
import time

# Seconds between forks. Small enough to sample quickly, large enough to avoid
# pinning a core at 100%.
INTERVAL_S = 0.05


def lsm_probe_fork() -> None:
    """Innermost frame: performs the actual fork() that fires task_alloc."""
    pid = os.fork()
    if pid == 0:
        # Child: exit immediately and cheaply, skipping atexit/flush handlers.
        os._exit(0)
    # Parent: reap the child so we do not leak zombies.
    os.waitpid(pid, 0)


def level_three() -> None:
    lsm_probe_fork()


def level_two() -> None:
    level_three()


def level_one() -> None:
    level_two()


def main() -> None:
    print(f"pid={os.getpid()} forking a child every {INTERVAL_S}s")
    print("expected python frames (top->bottom): "
          "lsm_probe_fork -> level_three -> level_two -> level_one -> main")
    print("press Ctrl+C to stop")
    count = 0
    try:
        while True:
            level_one()
            count += 1
            if count % 100 == 0:
                print(f"forked {count} times", flush=True)
            time.sleep(INTERVAL_S)
    except KeyboardInterrupt:
        print(f"\nstopped after {count} forks")
        sys.exit(0)


if __name__ == "__main__":
    main()
