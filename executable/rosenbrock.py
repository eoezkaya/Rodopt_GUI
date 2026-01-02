#!/usr/bin/env python3

import numpy as np
import time
import sys
import os

# Define the Rosenbrock function
def Rosenbrock(x):
    return (1 - x[0])**2 + 100 * (x[1] - x[0]**2)**2


def _read_delay_seconds(cfg_path: str, default: int) -> int:
    """
    Read delay_seconds from a simple config file.
    Expected line formats (examples):
      delay_seconds=21
      delay_seconds = 21
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
                    return int(float(v))
    except FileNotFoundError:
        return default
    except Exception:
        return default
    return default


def main():
    dim = 2
    input_filename = "dv.dat"
    output_filename = "rosenbrock.dat"

    # NEW: read from rosenbrock.cfg (fallback to default if missing/invalid)
    default_delay_seconds = 21
    cfg_path = "rosenbrock.cfg"
    delay_seconds = _read_delay_seconds(cfg_path, default_delay_seconds)

    try:
        # Read design variables
        with open(input_filename, "r") as f:
            dv = np.array([float(f.readline()) for _ in range(dim)])

        # Evaluate the function
        function_value = Rosenbrock(dv)

        # Optional delay
        time.sleep(delay_seconds)

        # Write the result (9 digits after decimal point)
        with open(output_filename, "w") as f:
            f.write(f"{function_value:.9f}\n")

    except Exception as e:
        print(f"Error in Rosenbrock evaluation: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

