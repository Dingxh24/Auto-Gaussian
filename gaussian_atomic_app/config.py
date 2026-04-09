from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

APP_NAME = 'GaussianAtomicWorkbench'
CONFIG_FILENAME = 'config.json'


def get_config_dir() -> Path:
    if os.name == 'nt':
        base = os.environ.get('APPDATA')
        if base:
            return Path(base) / APP_NAME
    return Path.home() / f'.{APP_NAME.lower()}'


def get_config_path() -> Path:
    return get_config_dir() / CONFIG_FILENAME


def default_config() -> dict[str, Any]:
    env_exe = os.environ.get('GAUSSIAN_EXE', '').strip()
    env_dir = os.environ.get('GAUSS_EXEDIR', '').strip()
    return {
        'gaussian_exe': env_exe,
        'gaussian_exe_dir': env_dir,
        'last_gjf_output_dir': '',
        'last_result_output_target': '',
        'last_selection': '',
    }


def load_config() -> dict[str, Any]:
    config = default_config()
    config_path = get_config_path()
    if not config_path.exists():
        return config

    try:
        loaded = json.loads(config_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return config

    if isinstance(loaded, dict):
        config.update(loaded)
    return config


def save_config(new_values: dict[str, Any]) -> dict[str, Any]:
    config = load_config()
    config.update(new_values)

    gaussian_exe = str(config.get('gaussian_exe', '')).strip()
    if gaussian_exe:
        exe_path = Path(gaussian_exe).expanduser().resolve()

        config['gaussian_exe'] = str(exe_path)
        config['gaussian_exe_dir'] = str(exe_path.parent)

    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    get_config_path().write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    return config
