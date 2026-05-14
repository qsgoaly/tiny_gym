"""Tiny Prometheus exporter for per-PID GPU memory.

DCGM Exporter reports device-level GPU stats (total VRAM, total SM util) but
not per-process. This sidecar polls NVML's
``nvmlDeviceGetComputeRunningProcesses`` every second and exposes:

  * ``gpu_process_memory_bytes{gpu, pid, process_name}``
    — VRAM bytes attributed to this PID on this GPU
  * ``gpu_process_count{gpu}``
    — number of processes currently using this GPU

The container needs:
  * the NVIDIA runtime device (``devices: nvidia.com/gpu=all``)
  * ``/proc`` mounted from host so we can resolve PID -> command line
"""

from __future__ import annotations

import os
import time

import pynvml
from prometheus_client import Gauge, start_http_server

g_mem = Gauge(
    "gpu_process_memory_bytes",
    "Per-process VRAM bytes used on a given GPU",
    ["gpu", "pid", "process_name"],
)
g_count = Gauge(
    "gpu_process_count",
    "Number of compute processes currently using this GPU",
    ["gpu"],
)


def _read_cmdline(pid: int) -> str:
    """Best-effort: read /hostfs/proc/<pid>/cmdline so we know what's running."""
    for base in ("/hostfs/proc", "/proc"):
        path = f"{base}/{pid}/cmdline"
        try:
            with open(path, "rb") as f:
                raw = f.read()
            parts = raw.split(b"\x00")
            # exe + first arg is usually enough to identify
            cmd = b" ".join(p for p in parts[:3] if p).decode("utf-8", errors="replace")
            if cmd:
                return cmd
        except (FileNotFoundError, PermissionError):
            continue
    return "?"


def collect_once(n_gpus: int) -> None:
    # Reset so dead processes drop off the chart.
    g_mem.clear()
    g_count.clear()
    for i in range(n_gpus):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        try:
            procs = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
        except pynvml.NVMLError:
            procs = []
        g_count.labels(gpu=str(i)).set(len(procs))
        for p in procs:
            cmd = _read_cmdline(p.pid)
            g_mem.labels(
                gpu=str(i), pid=str(p.pid), process_name=cmd[:120],
            ).set(p.usedGpuMemory or 0)


def main() -> None:
    pynvml.nvmlInit()
    n_gpus = pynvml.nvmlDeviceGetCount()
    interval = float(os.environ.get("NVML_PID_INTERVAL_S", "1.0"))
    port = int(os.environ.get("NVML_PID_PORT", "9401"))
    start_http_server(port)
    print(f"nvml-pid-exporter: serving /metrics on :{port}, "
          f"{n_gpus} GPU(s), interval={interval}s", flush=True)
    while True:
        collect_once(n_gpus)
        time.sleep(interval)


if __name__ == "__main__":
    main()
