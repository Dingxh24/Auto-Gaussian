from __future__ import annotations

from pathlib import Path
from typing import Callable

from .analyzer import calculate_properties, collect_energies, save_results
from .atomic_data import ELEMENTS
from .gaussian_runner import run_gaussian_for_file
from .gjf_generator import GeneratedFile, generate_gjf_files, parse_atomic_numbers

LogCallback = Callable[[str], None]
ProgressCallback = Callable[[str, int, int], None]


class WorkflowError(RuntimeError):
    pass


def _emit_progress(callback: ProgressCallback | None, step: str, current: int, total: int) -> None:
    if callback:
        callback(step, current, total)


def _emit_log(callback: LogCallback | None, message: str) -> None:
    if callback:
        callback(message)


def run_pipeline(
    *,
    selection: str,
    gjf_output_dir: str | Path,
    result_output_target: str | Path,
    gaussian_exe: str | Path,
    log: LogCallback | None = None,
    progress: ProgressCallback | None = None,
) -> dict[str, object]:
    atomic_numbers = parse_atomic_numbers(selection)
    symbols = [ELEMENTS[z] for z in atomic_numbers]
    gjf_dir = Path(gjf_output_dir).expanduser().resolve()

    _emit_log(log, f'已解析元素：{", ".join(f"{ELEMENTS[z]}(Z={z})" for z in atomic_numbers)}')
    _emit_progress(progress, '准备生成 .gjf 文件', 0, len(atomic_numbers))

    generated_files: list[GeneratedFile] = []
    for index, atomic_number in enumerate(atomic_numbers, start=1):
        generated = generate_gjf_files(atomic_number, gjf_dir)
        generated_files.extend(generated)
        _emit_log(log, f'已生成 {ELEMENTS[atomic_number]} 的 3 个 .gjf 文件。')
        _emit_progress(progress, '生成 .gjf 文件', index, len(atomic_numbers))

    _emit_progress(progress, '启动 Gaussian 计算', 0, len(generated_files))
    for index, generated in enumerate(generated_files, start=1):
        _emit_log(log, f'开始计算：{generated.file_path.name}')
        run_gaussian_for_file(gaussian_exe, generated.file_path, log=log)
        _emit_progress(progress, 'Gaussian 计算中', index, len(generated_files))

    _emit_log(log, '开始读取 .out / .log 并提取 SCF Done 能量。')
    energy_data = collect_energies(gjf_dir, allowed_symbols=symbols)

    _emit_log(log, '开始计算第一电离能、电子亲和能、化学势和 Mulliken 电负性。')
    dataframe = calculate_properties(energy_data)
    if dataframe.empty:
        raise WorkflowError('结果表为空，请检查 Gaussian 输出。')

    _emit_progress(progress, '保存结果表', 0, 1)
    xlsx_path, csv_path = save_results(dataframe, result_output_target)
    _emit_progress(progress, '保存结果表', 1, 1)

    _emit_log(log, f'Excel 已保存：{xlsx_path}')
    _emit_log(log, f'CSV 已保存：{csv_path}')

    return {
        'atomic_numbers': atomic_numbers,
        'symbols': symbols,
        'gjf_output_dir': str(gjf_dir),
        'xlsx_path': str(xlsx_path),
        'csv_path': str(csv_path),
        'generated_count': len(generated_files),
        'result_count': len(dataframe),
        'preview': dataframe.to_dict(orient='records'),
    }
