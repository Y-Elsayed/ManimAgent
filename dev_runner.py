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
    parser.add_argument("--media", default=None, help="Directory to store Manim media files.")
    parser.add_argument("--debug", default=None, help="Directory to store render stdout/stderr logs.")
    parser.add_argument("--attempts", type=int, default=1, help="Maximum repair attempts (default: 1).")

    args = parser.parse_args()

    code = load_script(args.file)
    file_name = os.path.splitext(os.path.basename(args.file))[0]
    media_dir = args.media or os.path.join(args.out, "media")
    final_dir = os.path.join(args.out, "final")
    debug_dir = args.debug or os.path.join(args.out, "debug")

    node = InterpreterNode()
    result = node.run(
        code=code,
        file_name=file_name,
        output_dir=args.out,
        media_dir=media_dir,
        final_dir=final_dir,
        debug_dir=debug_dir,
        max_attempts=args.attempts,
    )

    print("\n--- Run Summary ---")
    print(f"Script: {args.file}")
    print(f"Output dir: {args.out}")
    print(f"Media dir: {media_dir}")
    print(f"Debug dir: {debug_dir}")
    if result:
        print(f"Rendered scenes: {result.get('rendered')}")
        print(f"Failed scenes: {result.get('failed')}")
        print(f"Final video: {result.get('organized', {}).get('merged_video')}")
    else:
        print("No scenes rendered.")


if __name__ == "__main__":
    main()
