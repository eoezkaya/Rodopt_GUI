#!/usr/bin/env python3
import numpy as np
import sys
import time

def _read_delay_seconds(cfg_path: str, default: float) -> float:
    """
    Read delay_seconds from a simple config file.
    Expected line formats (examples):
      delay_seconds=0.5
      delay_seconds = 2
    Lines starting with # are ignored.
    """
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if "=" not in s:
                    continue
                k, v = (p.strip() for p in s.split("=", 1))
                if k == "delay_seconds":
                    return float(v)
    except FileNotFoundError:
        return default
    except Exception as e:
        print(f"Warning: Could not read delay_seconds from {cfg_path}: {e}", file=sys.stderr)
        return default
    return default


# --- Read delay configuration (if exists) ---
delay_seconds = _read_delay_seconds("constraint1.cfg", 0.0)
if delay_seconds > 0:
    time.sleep(delay_seconds)

# --- Read design vector ---
dim = 2
dv = np.zeros(dim)
with open("dv.dat", "r") as f:
    for i in range(dim):
        dv[i] = float(f.readline())

# --- Evaluate constraint ---
constraintValue = dv[0] + dv[1]

# --- Write output ---
with open("constraint1.dat", "w") as f:
    f.write(f"{constraintValue}\n")

