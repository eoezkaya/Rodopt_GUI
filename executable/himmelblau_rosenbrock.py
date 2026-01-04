import numpy as np
import time
import sys


def Himmelblau(x: np.ndarray) -> float:
    return (x[0] ** 2 + x[1] - 11) ** 2 + (x[0] + x[1] ** 2 - 7) ** 2


def Rosenbrock(x: np.ndarray, a: float = 1.0, b: float = 100.0) -> float:
    # Standard 2D Rosenbrock: (a - x)^2 + b(y - x^2)^2
    return (a - x[0]) ** 2 + b * (x[1] - x[0] ** 2) ** 2


def main():
    dim = 2
    input_filename = "dv.dat"
    output_himmelblau = "himmelblau.dat"
    output_rosenbrock = "rosenbrock.dat"
    delay_seconds = 31  # keep same behavior as himmelblau.py

    try:
        # Read design variables
        with open(input_filename, "r") as f:
            dv = np.array([float(f.readline()) for _ in range(dim)], dtype=float)

        # Evaluate functions
        himmelblau_value = Himmelblau(dv)
        rosenbrock_value = Rosenbrock(dv)

        # Optional delay
        time.sleep(delay_seconds)

        # Write results
        with open(output_himmelblau, "w") as f:
            f.write(f"{himmelblau_value:.9f}\n")

        with open(output_rosenbrock, "w") as f:
            f.write(f"{rosenbrock_value:.9f}\n")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()