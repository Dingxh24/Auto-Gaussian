from __future__ import annotations

from pathlib import Path
from typing import Any
import os

import webview

from .config import load_config, save_config
from .web import create_app


class DesktopAPI:
    def __init__(self) -> None:
        self.window: webview.Window | None = None

    def bind_window(self, window: webview.Window) -> None:
        self.window = window

    def _ensure_window(self) -> webview.Window:
        if self.window is None:
            raise RuntimeError('窗口尚未初始化。')
        return self.window

    def choose_gaussian_exe(self) -> dict[str, Any]:
        window = self._ensure_window()
        result = window.create_file_dialog(
            webview.FileDialog.OPEN,
            file_types=('Executable (*.exe)', 'All files (*.*)'),
        )
        if not result:
            return {'ok': False, 'cancelled': True}
        file_path = Path(result[0]).expanduser().resolve()
        config = save_config({'gaussian_exe': str(file_path)})
        return {'ok': True, 'path': str(file_path), 'config': config}

    def choose_output_folder(self) -> dict[str, Any]:
        window = self._ensure_window()
        result = window.create_file_dialog(webview.FileDialog.FOLDER)
        if not result:
            return {'ok': False, 'cancelled': True}
        return {'ok': True, 'path': str(Path(result[0]).expanduser().resolve())}

    def choose_result_file(self) -> dict[str, Any]:
        window = self._ensure_window()
        config = load_config()
        default_dir = config.get('last_result_output_target') or config.get('last_gjf_output_dir') or str(Path.home())
        directory = default_dir if Path(str(default_dir)).suffix == '' else str(Path(str(default_dir)).parent)
        result = window.create_file_dialog(
            webview.FileDialog.SAVE,
            directory=directory,
            save_filename='原子能性质汇总.xlsx',
            file_types=('Excel Workbook (*.xlsx)', 'CSV (*.csv)', 'All files (*.*)'),
        )
        if not result:
            return {'ok': False, 'cancelled': True}
        return {'ok': True, 'path': str(Path(result[0]).expanduser().resolve())}

    def get_config(self) -> dict[str, Any]:
        return {'ok': True, 'config': load_config()}


def launch_desktop_app() -> None:
    api = DesktopAPI()
    app = create_app()
    window = webview.create_window(
        'Gaussian 原子能性质计算器',
        app,
        js_api=api,
        width=1100,
        height=820,
        min_size=(980, 720),
        resizable=True,
        text_select=True,
    )
    api.bind_window(window)
    gui = os.environ.get('GAW_WEBVIEW_GUI', '').strip() or None
    if gui:
        webview.start(debug=False, gui=gui)
    else:
        webview.start(debug=False)
