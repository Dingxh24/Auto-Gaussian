from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
import time
import ctypes
from typing import Callable


@dataclass(slots=True)
class GaussianRunResult:
    gjf_file: Path
    return_code: int
    stdout: str
    stderr: str


def build_runtime_env(gaussian_exe: str | Path) -> dict[str, str]:
    exe_path = Path(gaussian_exe).expanduser().resolve()
    env = os.environ.copy()
    env['GAUSS_EXEDIR'] = str(exe_path.parent)
    env['PATH'] = f"{exe_path.parent}{os.pathsep}{env.get('PATH', '')}"
    return env


def _to_short_path(path: Path) -> Path:
    """
    Windows 下将路径转换为 8.3 短路径，尽量规避部分程序对空格/非 ASCII 路径的兼容性问题。
    若转换失败则返回原路径。
    """
    if os.name != 'nt':
        return path

    buffer_len = 4096
    buffer = ctypes.create_unicode_buffer(buffer_len)
    try:
        get_short = ctypes.windll.kernel32.GetShortPathNameW  # type: ignore[attr-defined]
    except Exception:
        return path

    try:
        rc = int(get_short(str(path), buffer, buffer_len))
    except Exception:
        return path

    if rc <= 0:
        return path
    return Path(buffer.value)


def _tail_text(path: Path, *, max_bytes: int = 65536) -> str:
    try:
        with open(path, 'rb') as handle:
            try:
                handle.seek(-max_bytes, os.SEEK_END)
            except OSError:
                handle.seek(0)
            data = handle.read()
    except OSError:
        return ''
    return data.decode('utf-8', errors='ignore')


def _guess_output_file(gjf_file: Path) -> Path | None:
    for suffix in ('.log', '.out'):
        candidate = gjf_file.with_suffix(suffix)
        if candidate.exists():
            return candidate
    return None


def _output_candidates(gjf_file: Path) -> list[Path]:
    return [gjf_file.with_suffix('.log'), gjf_file.with_suffix('.out')]


def _stat_signature(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return (int(stat.st_mtime_ns), int(stat.st_size))


def run_gaussian_for_file(
    gaussian_exe: str | Path,
    gjf_path: str | Path,
    *,
    timeout: int | None = None,
    output_wait_seconds: float = 2.0,
    log: Callable[[str], None] | None = None,
) -> GaussianRunResult:
    gjf_file = Path(gjf_path).expanduser().resolve()
    exe_path = Path(gaussian_exe).expanduser().resolve()

    if not exe_path.exists():
        raise FileNotFoundError(f'Gaussian 可执行文件不存在：{exe_path}')
    if not gjf_file.exists():
        raise FileNotFoundError(f'.gjf 文件不存在：{gjf_file}')

    env = build_runtime_env(exe_path)

    # 额外保险：尽量使用短路径启动，减少空格/非 ASCII 路径带来的不确定性。
    exe_path = _to_short_path(exe_path)
    work_dir = _to_short_path(gjf_file.parent)

    # 与用户 bat 调用方式一致：在 .gjf 所在目录作为工作目录，只传入文件名。
    # 这样可以避免某些 Gaussian 版本/环境对带空格或非 ASCII 的绝对路径兼容性较差的问题。
    cmd = [str(exe_path), str(gjf_file.name)]

    runner_log = gjf_file.with_suffix('.runner.log')

    if log:
        log(f'启动 Gaussian：{" ".join(cmd)}')
        log(f'工作目录：{work_dir}')
        log(f'GAUSS_EXEDIR：{env.get("GAUSS_EXEDIR", "")}')
        log(f'runner 日志：{runner_log}')
        log('提示：计算过程通常不会弹出窗口；请留意同目录下 .log/.out 是否持续增长。')

    creationflags = 0
    if os.name == 'nt' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
        creationflags = int(subprocess.CREATE_NO_WINDOW)

    candidates = _output_candidates(gjf_file)
    before_stats: dict[Path, tuple[int, int] | None] = {p: _stat_signature(p) for p in candidates}
    start_ts = time.time()

    with open(runner_log, 'wb') as handle:
        header = '\n'.join(
            [
                f'[GaussianAtomicWorkbench] start={start_ts:.3f}',
                f'cmd={" ".join(cmd)}',
                f'cwd={work_dir}',
                f'GAUSS_EXEDIR={env.get("GAUSS_EXEDIR", "")}',
                '',
            ]
        ).encode('utf-8', errors='ignore')
        handle.write(header)
        handle.flush()
        completed = subprocess.run(
            cmd,
            cwd=str(work_dir),
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )

    result = GaussianRunResult(
        gjf_file=gjf_file,
        return_code=completed.returncode,
        stdout='',
        stderr='',
    )

    def pick_updated_output() -> Path | None:
        updated: list[tuple[int, Path]] = []
        for path in candidates:
            sig = _stat_signature(path)
            if sig is None:
                continue
            before = before_stats.get(path)
            if before is None:
                # 之前不存在，现在有了
                updated.append((sig[0], path))
            else:
                # 之前存在，检查是否有更新（mtime/size 任一变化）
                if sig != before:
                    updated.append((sig[0], path))
        if not updated:
            return None
        updated.sort(key=lambda item: item[0])
        return updated[-1][1]

    output_file: Path | None = pick_updated_output()
    if output_file is None and output_wait_seconds > 0:
        start = time.monotonic()
        while time.monotonic() - start < output_wait_seconds:
            output_file = pick_updated_output()
            if output_file is not None:
                break
            time.sleep(0.1)

    output_tail = _tail_text(output_file) if output_file is not None else ''
    normal_termination = 'Normal termination' in output_tail
    error_termination = 'Error termination' in output_tail

    # 有些环境下 return code 可能非 0，但输出仍然正常终止；此时不应直接判定失败。
    if result.return_code != 0 and normal_termination:
        if log:
            log(f'Gaussian 返回码为 {result.return_code}，但输出显示正常结束：{output_file.name if output_file else "(未知输出)"}')

    if output_file is None:
        raise RuntimeError(
            '\n'.join(
                [
                    f'Gaussian 未生成或未更新 .log/.out：{gjf_file.name}',
                    f'工作目录：{work_dir}',
                    f'返回码：{result.return_code}',
                    f'runner 日志：{runner_log}',
                    f'runner 尾部:\n{_tail_text(runner_log).strip()}' if _tail_text(runner_log).strip() else 'runner 尾部: <空>',
                ]
            )
        )

    if error_termination or (result.return_code != 0 and not normal_termination) or (result.return_code == 0 and not normal_termination):
        raise RuntimeError(
            '\n'.join(
                [
                    f'Gaussian 执行失败：{gjf_file.name}',
                    f'工作目录：{work_dir}',
                    f'返回码：{result.return_code}',
                    f'输出文件：{output_file}',
                    f'输出尾部:\n{output_tail.strip()}' if output_tail.strip() else '输出尾部: <空>',
                    f'runner 日志：{runner_log}',
                    f'runner 尾部:\n{_tail_text(runner_log).strip()}' if _tail_text(runner_log).strip() else 'runner 尾部: <空>',
                ]
            )
        )

    if log:
        log(f'Gaussian 完成：{gjf_file.name}')

    return result
