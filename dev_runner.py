"""
Development runner for ManimAgent.
Use this to test and debug generated Manim scripts directly
without running the entire LLM pipeline.

Example:
    python dev_runner.py --file projects/eigen_values_and_vectors/output/eigenvalues_and_eigenvectors.py
"""

import argparse
import os
import re
from nodes.interpreter_node import InterpreterNode


def load_script(path: str):
    """Read a Manim script from file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Script not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(description="Run a specific Manim script using InterpreterNode.")
    parser.add_argument("--file", required=True, help="Path to the .py file containing Manim scenes.")
    parser.add_argument("--out", default="dev_output", help="Directory to store temporary output.")
    parser.add_argument("--attempts", type=int, default=1, help="Maximum repair attempts (default: 1).")

    args = parser.parse_args()

    code = load_script(args.file)
    file_name = os.path.splitext(os.path.basename(args.file))[0]

    node = InterpreterNode()
    result = node.run(code=code, file_name=file_name, output_dir=args.out, max_attempts=args.attempts)

    print("\n--- Run Summary ---")
    print(f"Script: {args.file}")
    print(f"Output dir: {args.out}")
    print(f"Rendered scenes: {result.get('rendered')}")
    print(f"Failed scenes: {result.get('failed')}")


if __name__ == "__main__":
    main()
