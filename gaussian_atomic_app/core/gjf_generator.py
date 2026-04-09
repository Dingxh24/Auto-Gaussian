from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .atomic_data import ELEMENTS, ORBITAL_INFO, ORBITALS, NEUTRAL_EXCEPTIONS


@dataclass(slots=True)
class GeneratedFile:
    atomic_number: int
    symbol: str
    charge: int
    multiplicity: int
    file_path: Path


def build_neutral_configuration(z: int) -> dict[str, int]:
    """生成中性原子的近似基态电子排布。"""
    remaining = z
    config = {name: 0 for name, *_ in ORBITALS}

    for name, _, _, cap in ORBITALS:
        if remaining <= 0:
            break
        put = min(cap, remaining)
        config[name] = put
        remaining -= put

    if z in NEUTRAL_EXCEPTIONS:
        config.update(NEUTRAL_EXCEPTIONS[z])

    return config


def remove_one_electron(config: dict[str, int]) -> None:
    """阳离子：优先从最高主量子数 n 的轨道移去电子；若 n 相同，再从 l 更大的轨道移去。"""
    occupied = [orb for orb, occ in config.items() if occ > 0]
    target = max(
        occupied,
        key=lambda orb: (
            ORBITAL_INFO[orb]['n'],
            ORBITAL_INFO[orb]['l'],
            ORBITAL_INFO[orb]['index'],
        ),
    )
    config[target] -= 1


def add_one_electron(config: dict[str, int]) -> None:
    """阴离子：按 Aufbau 顺序向未满轨道补电子。"""
    for orb, *_ in ORBITALS:
        if config[orb] < ORBITAL_INFO[orb]['cap']:
            config[orb] += 1
            return
    raise ValueError('电子数超出当前轨道定义范围。')


def get_ionic_configuration(z: int, charge: int) -> dict[str, int]:
    config = build_neutral_configuration(z)
    if charge > 0:
        for _ in range(charge):
            remove_one_electron(config)
    elif charge < 0:
        for _ in range(-charge):
            add_one_electron(config)
    return config


def count_unpaired_electrons(config: dict[str, int]) -> int:
    """按 Hund 规则估算每个亚层中的未成对电子数。"""
    total = 0
    for orb, occ in config.items():
        if occ <= 0:
            continue
        deg = ORBITAL_INFO[orb]['deg']
        total += occ if occ <= deg else (2 * deg - occ)
    return total


def get_multiplicity(z: int, charge: int) -> int:
    electron_count = z - charge
    if electron_count < 0:
        raise ValueError('该电荷下电子数小于 0，无法生成合理的单原子 Gaussian 输入文件。')
    if electron_count == 0:
        return 1
    config = get_ionic_configuration(z, charge)
    return count_unpaired_electrons(config) + 1


def make_gjf_text(symbol: str, charge: int, multiplicity: int, output_dir: Path) -> str:
    suffix = '+' if charge == 1 else '-' if charge == -1 else ''
    chk_path = str(output_dir / f'{symbol}{suffix}.chk').replace('/', '\\')

    if charge in (0, 1):
        route = '# wb97xd geom=connectivity def2tzvp'
    else:
        route = '# wb97xd geom=connectivity aug-cc-pvtz'

    return (
        f'%chk={chk_path}\r\n'
        f'{route}\r\n'
        f'\r\n'
        f'Title Card Required\r\n'
        f'\r\n'
        f'{charge} {multiplicity}\r\n'
        f'  {symbol:<2}                 0.00000000    0.00000000    0.00000000\r\n'
        f'\r\n'
        f'1\r\n'
    )


def parse_atomic_numbers(selection: str, *, min_z: int = 1, max_z: int = 118) -> list[int]:
    """
    解析用户输入的原子序数选择。

    支持格式：
    - "1,2,3"
    - "1-3"
    - "1-3,5"

    分隔符支持英文/中文逗号、分号以及空白字符。返回去重后的顺序列表。
    """
    text = selection.strip()
    if not text:
        raise ValueError('输入不能为空。')

    text = (
        text.replace('，', ',')
        .replace('；', ';')
        .replace('–', '-')
        .replace('—', '-')
        .replace('－', '-')
    )
    text = re.sub(r'\s*-\s*', '-', text)

    tokens = [t for t in re.split(r'[\s,;]+', text) if t]
    if not tokens:
        raise ValueError('未解析到任何有效的原子序数。')

    result: list[int] = []
    seen: set[int] = set()

    def add_z(z: int) -> None:
        if not (min_z <= z <= max_z):
            raise ValueError(f'原子序数必须在 {min_z} 到 {max_z} 之间：{z}')
        if z not in seen:
            seen.add(z)
            result.append(z)

    for token in tokens:
        if '-' in token:
            parts = token.split('-', 1)
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise ValueError(f'范围格式无效：{token}')
            if not parts[0].isdigit() or not parts[1].isdigit():
                raise ValueError(f'范围必须是数字：{token}')
            start = int(parts[0])
            end = int(parts[1])
            if start > end:
                raise ValueError(f'范围起止顺序错误（应为 小-大）：{token}')
            for z in range(start, end + 1):
                add_z(z)
        else:
            if not token.isdigit():
                raise ValueError(f'原子序数必须是数字：{token}')
            add_z(int(token))

    return result


def generate_gjf_files(atomic_number: int, output_dir: str | Path) -> list[GeneratedFile]:
    if not (1 <= atomic_number <= 118):
        raise ValueError('原子序数必须在 1 到 118 之间。')

    symbol = ELEMENTS[atomic_number]
    out_path = Path(output_dir).expanduser().resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    generated: list[GeneratedFile] = []
    for charge in (1, 0, -1):
        multiplicity = get_multiplicity(atomic_number, charge)
        suffix = '+' if charge == 1 else '-' if charge == -1 else ''
        file_path = out_path / f'{symbol}{suffix}.gjf'
        gjf_text = make_gjf_text(symbol, charge, multiplicity, out_path)
        file_path.write_text(gjf_text, encoding='utf-8', newline='')
        generated.append(
            GeneratedFile(
                atomic_number=atomic_number,
                symbol=symbol,
                charge=charge,
                multiplicity=multiplicity,
                file_path=file_path,
            )
        )
    return generated
