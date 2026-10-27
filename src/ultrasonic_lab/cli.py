"""Explicit local analysis; no instrument control or network operation."""

import argparse
import csv
import sys
from pathlib import Path

from . import __version__
from .workflow import analyze_file, run_benchmark


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Offline pulse-echo research lab; no verified physical crack detector."
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    benchmark = sub.add_parser("benchmark", help="Run the frozen, explicitly synthetic experiment.")
    benchmark.add_argument("--output", type=Path, required=True)
    analyze = sub.add_parser(
        "analyze", help="Analyze one local CSV without a physical crack decision."
    )
    analyze.add_argument("--trace", type=Path, required=True)
    analyze.add_argument("--metadata", type=Path, required=True)
    analyze.add_argument("--settings", type=Path)
    analyze.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "benchmark":
            metrics = run_benchmark(args.output)
            print(
                f"Synthetic specimens: {metrics['specimen_count']}; threshold: {metrics['threshold_fit']['value']:.5f}"
            )
        else:
            metrics = analyze_file(args.trace, args.metadata, args.output, args.settings)
            print(
                f"Capture status: {metrics['result']['status']}; physical crack decision: not evaluated"
            )
        print(f"Report: {args.output / 'index.html'}")
        return 0
    except (OSError, ValueError, csv.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
