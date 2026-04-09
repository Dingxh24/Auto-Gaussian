from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_pyinstaller() -> bool:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        return False
    return True


def _run(cmd: list[str]) -> int:
    print('> ' + ' '.join(cmd))
    completed = subprocess.run(cmd, check=False)
    return int(completed.returncode)


def build_onedir(pyinstaller: list[str], root: Path, distpath: Path | None, workpath: Path | None) -> int:
    cmd = [
        *pyinstaller,
        str(root / 'build' / 'windows' / 'GaussianAtomicWorkbench.spec'),
        '--noconfirm',
    ]
    if distpath is not None:
        cmd.extend(['--distpath', str(distpath)])
    if workpath is not None:
        cmd.extend(['--workpath', str(workpath)])
    return _run(cmd)


def build_onefile(pyinstaller: list[str], root: Path, distpath: Path | None, workpath: Path | None) -> int:
    templates = root / 'gaussian_atomic_app' / 'templates'
    static = root / 'gaussian_atomic_app' / 'static'

    cmd = [
        *pyinstaller,
        str(root / 'main.py'),
        '--noconfirm',
        '--clean',
        '--onefile',
        '--windowed',
        '--name',
        'GaussianAtomicWorkbench',
        '--add-data',
        f'{templates};templates',
        '--add-data',
        f'{static};static',
    ]
    if distpath is not None:
        cmd.extend(['--distpath', str(distpath)])
    if workpath is not None:
        cmd.extend(['--workpath', str(workpath)])
    return _run(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description='Build GaussianAtomicWorkbench executable (Windows/PyInstaller).')
    parser.add_argument(
        '--mode',
        choices=('onedir', 'onefile'),
        default='onedir',
        help='onedir: dist/GaussianAtomicWorkbench/..., onefile: dist/GaussianAtomicWorkbench.exe',
    )
    parser.add_argument('--distpath', default='', help='Custom dist output directory (optional).')
    parser.add_argument('--workpath', default='', help='Custom build work directory (optional).')
    args = parser.parse_args()

    if sys.platform != 'win32':
        print('This build script targets Windows (.exe).')
        return 2

    if not _ensure_pyinstaller():
        print('PyInstaller is not installed. Run: pip install pyinstaller')
        return 2

    root = _project_root()
    os.chdir(root)

    pyinstaller = [sys.executable, '-m', 'PyInstaller']

    distpath = Path(args.distpath).expanduser().resolve() if args.distpath else None
    workpath = Path(args.workpath).expanduser().resolve() if args.workpath else None

    if args.mode == 'onefile':
        return build_onefile(pyinstaller, root, distpath, workpath)
    return build_onedir(pyinstaller, root, distpath, workpath)


if __name__ == '__main__':
    raise SystemExit(main())

