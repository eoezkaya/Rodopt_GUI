#!/usr/bin/env python3
import numpy as np
import sys
import time

# --- Read delay configuration (if exists) ---
delay_seconds = 0.0
try:
    with open("constraint.cfg", "r") as fcfg:
        line = fcfg.readline().strip()
        delay_seconds = float(line)
        time.sleep(delay_seconds)
except FileNotFoundError:
    pass  # no delay if cfg missing
except Exception as e:
    print(f"Warning: Could not read delay: {e}")

# --- Read design vector ---
dim = 2
dv = np.zeros(dim)
with open(f"dv.dat", "r") as f:
    for i in range(dim):
        dv[i] = float(f.readline())

# --- Evaluate constraint ---
constraintValue = dv[0] + dv[1]

# --- Write output ---
with open(f"constraint1.dat", "w") as f:
    f.write(f"{constraintValue}\n")

