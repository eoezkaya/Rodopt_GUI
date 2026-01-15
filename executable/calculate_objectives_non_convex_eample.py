#!/usr/bin/env python3

import numpy as np
import time


def evaluateFunction1(x: np.ndarray) -> float:
    x1 = float(x[0])
    x2 = float(x[1])
    term1 = 3 * (1 - x1) ** 2 * np.exp(-x1**2 - (x2 + 1) ** 2)
    term2 = 10 * (x1 / 5 - x1**3 - x2**5) * np.exp(-x1**2 - x2**2)
    term3 = -3 * np.exp(-(x1 + 2) ** 2 - x2**2)
    term4 = 0.5 * (2 * x1 + x2)
    return float(-(term1 + term2 + term3 + term4))


def evaluateFunction2(x: np.ndarray) -> float:
    x1 = float(x[0])
    x2 = float(x[1])
    term1 = 3 * (1 + x2) ** 2 * np.exp(-(1 - x1) ** 2 - x2**2)
    term2 = -10 * (-x2 / 5 + x2**3 + x1**5) * np.exp(-x1**2 - x2**2)
    term3 = -3 * np.exp(-(2 - x2) ** 2 - x1**2)
    return float(-(term1 + term2 + term3))


def main() -> int:
    print("Evaluating objective functions...\n")

    dim = 2
    dv = np.zeros(dim, dtype=float)

    try:
        with open("dv.dat", "r", encoding="utf-8") as f:
            for i in range(dim):
                line = f.readline()
                if not line:
                    raise ValueError(f"dv.dat ended early at line {i + 1} (expected {dim} values).")
                dv[i] = float(line.strip())
    except Exception as e:
        print(f"ERROR: Failed to read dv.dat: {e}")
        return 1

    print("design variables =", dv)

    functionValue1 = evaluateFunction1(dv)
    functionValue2 = evaluateFunction2(dv)

    print("function1 value =", functionValue1)
    print("function2 value =", functionValue2)

    # NEW: delay before writing results
    time.sleep(50)

    try:
        with open("f1.dat", "w", encoding="utf-8") as f:
            f.write(f"{functionValue1}\n")
        with open("f2.dat", "w", encoding="utf-8") as f:
            f.write(f"{functionValue2}\n")
    except Exception as e:
        print(f"ERROR: Failed to write output files: {e}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

