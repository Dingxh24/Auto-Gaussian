from __future__ import annotations

import argparse
from pathlib import Path

from gaussian_atomic_app.core.gaussian_runner import run_gaussian_for_file


def main() -> int:
    parser = argparse.ArgumentParser(description='Run Gaussian for a single .gjf file (debug helper).')
    parser.add_argument('--gaussian-exe', required=True, help='Path to g16.exe / g09.exe')
    parser.add_argument('--gjf', required=True, help='Path to .gjf file')
    parser.add_argument('--timeout', type=int, default=0, help='Timeout seconds (0 = no timeout)')
    args = parser.parse_args()

    gaussian_exe = str(Path(args.gaussian_exe).expanduser())
    gjf = str(Path(args.gjf).expanduser())
    timeout = None if args.timeout <= 0 else int(args.timeout)

    def log(message: str) -> None:
        print(message, flush=True)

    run_gaussian_for_file(gaussian_exe, gjf, timeout=timeout, log=log)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

