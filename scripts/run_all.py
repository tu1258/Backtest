from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print("\n$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build data then run backtest.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--years", type=int, default=None)
    parser.add_argument("--max-tickers", type=int, default=None)
    parser.add_argument("--output-dir", default="outputs/backtest")
    args = parser.parse_args()

    py = sys.executable
    build = [py, "scripts/build_data.py", "--config", args.config]
    if args.years is not None:
        build += ["--years", str(args.years)]
    if args.max_tickers is not None:
        build += ["--max-tickers", str(args.max_tickers)]
    run(build)

    backtest = [py, "scripts/run_backtest.py", "--config", args.config, "--output-dir", args.output_dir]
    run(backtest)


if __name__ == "__main__":
    main()
