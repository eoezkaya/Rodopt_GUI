#!/usr/bin/env python3

import numpy as np
import time
import sys

# Define the Rosenbrock function
def Rosenbrock(x):
    return (1 - x[0])**2 + 100 * (x[1] - x[0]**2)**2


def main():
    

    dim = 2
    input_filename = f"dv.dat"
    output_filename = f"rosenbrock.dat"
    delay_seconds = 21  # Delay in seconds

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
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

