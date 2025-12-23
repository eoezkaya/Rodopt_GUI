#!/usr/bin/env python3
import sys
import os
import time
import numpy as np


def evaluate_function(x: np.ndarray) -> float:
    """Example nonlinear function with 42 variables."""
    if x.size != 42:
        raise ValueError(f"Expected 42 design variables, got {x.size}.")
    # Nonlinear, multimodal, smooth
    return np.sum(x**2 + 0.5 * np.sin(3 * x) + 0.2 * x**4)


def main():
    
    # --- Filenames ---
    input_filename = f"dv.dat"
    output_filename = f"synthetic.dat"
    config_filename = "synthetic.cfg"

    # --- Read delay configuration ---
    delay = 0.0
    try:
        with open(config_filename, "r") as cfg:
            line = cfg.readline().strip()
            delay = float(line)
    except FileNotFoundError:
        print(f"Warning: {config_filename} not found → using delay = 0.0 s")
    except ValueError:
        print(f"Warning: Invalid delay value in {config_filename} → using delay = 0.0 s")
    except Exception as e:
        print(f"Warning: Could not read {config_filename}: {e}")

    # --- Read design vector ---
    try:
        dv = np.atleast_1d(np.loadtxt(input_filename))
    except Exception as e:
        print(f"Error reading {input_filename}: {e}", file=sys.stderr)
        sys.exit(1)

    if dv.size != 42:
        print(f"Error: Expected 42 variables, but got {dv.size}.", file=sys.stderr)
        sys.exit(1)

    # --- Evaluate function ---
    try:
        fval = evaluate_function(dv)
    except Exception as e:
        print(f"Error evaluating function: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Optional delay ---
    if delay > 0:
        time.sleep(delay)

    # --- Write output safely ---
    tmp_file = output_filename + ".tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(f"{fval:.12f}\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, output_filename)
    except Exception as e:
        print(f"Error writing {output_filename}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

