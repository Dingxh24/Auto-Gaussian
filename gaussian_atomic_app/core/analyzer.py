from __future__ import annotations

from pathlib import Path
import math
import re
from typing import Iterable

import pandas as pd

from .atomic_data import ATOMIC_NUMBER, HARTREE_TO_EV


def extract_last_scf_energy(file_path: Path) -> float | None:
    """
    提取结果文件中最后一个 'SCF Done:' 对应的能量值。
    兼容 .out / .log。
    """
    pattern = re.compile(r"SCF Done:\s+E\([^)]+\)\s*=\s*([-\d\.]+)")
    last_energy = None

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as handle:
        for line in handle:
            match = pattern.search(line)
            if match:
                last_energy = float(match.group(1))

    return last_energy


def parse_result_filename(file_path: Path) -> tuple[str | None, int | None]:
    """
    从文件名判断元素符号和电荷状态。

    支持：
    - Al.out / Al.log      -> 中性态
    - Al+.out / Al+.log    -> 正离子
    - Al-.out / Al-.log    -> 负离子
    - Al+1.out / Al+1.log  -> 正离子
    - Al-1.out / Al-1.log  -> 负离子
    """
    stem = file_path.stem.strip()
    matched = re.fullmatch(r'([A-Z][a-z]?)([+-](?:1)?)?', stem)
    if not matched:
        return None, None

    symbol = matched.group(1)
    charge_part = matched.group(2)

    if symbol not in ATOMIC_NUMBER:
        return None, None

    if charge_part is None:
        charge = 0
    elif charge_part.startswith('+'):
        charge = +1
    elif charge_part.startswith('-'):
        charge = -1
    else:
        return None, None

    return symbol, charge


def hartree_to_ev(value: float | None) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return value * HARTREE_TO_EV


def safe_round(value: float | None, ndigits: int = 2) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(value, ndigits)


def _candidate_files(input_path: Path) -> list[Path]:
    files = list(input_path.glob('*.out')) + list(input_path.glob('*.log'))
    return sorted(files, key=lambda p: p.stat().st_mtime)


def collect_energies(input_dir: str | Path, allowed_symbols: Iterable[str] | None = None) -> dict[str, dict[int, float]]:
    """
    扫描目录中的 .out / .log 文件，并提取每个元素正/中/负电荷的能量。

    如果同一元素-电荷组合对应多个结果文件，则采用最后修改时间最新的那个文件。
    """
    data: dict[str, dict[int, float]] = {}
    source_map: dict[tuple[str, int], Path] = {}

    input_path = Path(input_dir).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f'结果目录不存在：{input_path}')

    symbols_filter = set(allowed_symbols) if allowed_symbols else None
    output_files = _candidate_files(input_path)

    if not output_files:
        raise FileNotFoundError(f'目录中未找到 .out 或 .log 文件：{input_path}')

    for file_path in output_files:
        symbol, charge = parse_result_filename(file_path)
        if symbol is None:
            continue
        if symbols_filter is not None and symbol not in symbols_filter:
            continue

        energy = extract_last_scf_energy(file_path)
        if energy is None:
            continue

        if symbol not in data:
            data[symbol] = {}

        data[symbol][charge] = energy
        source_map[(symbol, charge)] = file_path

    if not data:
        if symbols_filter:
            symbols_text = ', '.join(sorted(symbols_filter))
            raise FileNotFoundError(f'未在结果目录中找到指定元素的有效结果：{symbols_text}')
        raise FileNotFoundError('未找到可解析的有效结果文件。')

    return data


def calculate_properties(energy_data: dict[str, dict[int, float]]) -> pd.DataFrame:
    rows: list[dict[str, float | int | str | None]] = []

    for symbol in sorted(energy_data.keys(), key=lambda s: ATOMIC_NUMBER[s]):
        energies = energy_data[symbol]
        e_cation = energies.get(+1)
        e_neutral = energies.get(0)
        e_anion = energies.get(-1)

        if e_cation is not None and e_neutral is not None:
            i1_ev = hartree_to_ev(e_cation - e_neutral)
        else:
            i1_ev = None

        if e_neutral is not None and e_anion is not None:
            a_ev = hartree_to_ev(e_neutral - e_anion)
        else:
            a_ev = None

        if e_cation is not None and e_anion is not None:
            mu_ev = hartree_to_ev((e_anion - e_cation) / 2.0)
        else:
            mu_ev = None

        if i1_ev is not None and a_ev is not None:
            chi = (i1_ev + a_ev) / 2.0
        else:
            chi = None

        rows.append(
            {
                '原子序数': ATOMIC_NUMBER[symbol],
                '元素符号': symbol,
                '正离子能量（Hartree）': safe_round(e_cation, 6),
                '中性态能量（Hartree）': safe_round(e_neutral, 6),
                '负离子能量（Hartree）': safe_round(e_anion, 6),
                '第一电离能（eV）': safe_round(i1_ev, 6),
                '电子亲和能（eV）': safe_round(a_ev, 6),
                '化学势（eV）': safe_round(mu_ev, 6),
                'Mulliken 电负性': safe_round(chi, 6),
            }
        )

    return pd.DataFrame(rows)


def resolve_result_paths(output_target: str | Path) -> tuple[Path, Path]:
    target = Path(output_target).expanduser().resolve()

    if target.suffix.lower() == '.xlsx':
        xlsx_path = target
        csv_path = target.with_suffix('.csv')
    elif target.suffix.lower() == '.csv':
        csv_path = target
        xlsx_path = target.with_suffix('.xlsx')
    elif target.suffix:
        raise ValueError('结果输出路径请使用 .xlsx / .csv，或直接提供一个目录。')
    else:
        target.mkdir(parents=True, exist_ok=True)
        xlsx_path = target / '原子能性质汇总.xlsx'
        csv_path = target / '原子能性质汇总.csv'

    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    return xlsx_path, csv_path


def save_results(df: pd.DataFrame, output_target: str | Path) -> tuple[Path, Path]:
    if df.empty:
        raise ValueError('结果表为空，无法保存。')

    xlsx_path, csv_path = resolve_result_paths(output_target)
    df.to_excel(xlsx_path, index=False)
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    return xlsx_path, csv_path
