#!/usr/bin/env python3
import sys
import os
import time
import numpy as np

# --- Add both the script dir and the current working dir to sys.path ---
script_dir = os.path.dirname(os.path.abspath(__file__))
run_dir = os.getcwd()

for path in (run_dir, script_dir):
    if path not in sys.path:
        sys.path.insert(0, path)

from rosenbrock_optimization import RosenbrockOptimization  # ✅ use Rosenbrock version


def main():
    
    # --- Filenames ---
    input_filename = f"dv.dat"
    output_filename = f"rosenbrock.dat"
    config_filename = "rosenbrock.cfg"

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
        dv = np.loadtxt(input_filename)
    except Exception as e:
        print(f"Error reading {input_filename}: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Evaluate function ---
    rosenbrockOpt = RosenbrockOptimization(a=1.0, b=100.0)
    try:
        function_value = rosenbrockOpt.evaluateFunction(dv)
    except Exception as e:
        print(f"Error evaluating Rosenbrock function: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Apply delay if specified ---
    if delay > 0:
        time.sleep(delay)

    # --- Write output safely ---
    tmp_file = output_filename + ".tmp"
    try:
        with open(tmp_file, "w") as f:
            f.write(f"{function_value:.12f}\n")
        os.replace(tmp_file, output_filename)
    except Exception as e:
        print(f"Error writing {output_filename}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
