from __future__ import annotations

from pathlib import Path
from threading import Thread
from typing import Any
import sys

from flask import Flask, jsonify, render_template, request

from .config import load_config, save_config
from .core.workflow import run_pipeline
from .jobs import job_store


def _resource_path(relative: str) -> str:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent
    return str(base / relative)


TEMPLATE_DIR = _resource_path('templates')
STATIC_DIR = _resource_path('static')


def create_app() -> Flask:
    app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
    app.config['JSON_AS_ASCII'] = False

    @app.get('/')
    def index():
        return render_template('index.html', config=load_config())

    @app.get('/api/config')
    def get_config():
        config = load_config()
        configured = bool(config.get('gaussian_exe')) and Path(config['gaussian_exe']).exists()
        return jsonify({'ok': True, 'config': config, 'configured': configured})

    @app.post('/api/config')
    def update_config():
        payload: dict[str, Any] = request.get_json(silent=True) or {}
        gaussian_exe = str(payload.get('gaussian_exe', '')).strip()

        if not gaussian_exe:
            return jsonify({'ok': False, 'error': '请先提供 Gaussian 可执行文件路径。'}), 400

        exe_path = Path(gaussian_exe).expanduser().resolve()
        if not exe_path.exists():
            return jsonify({'ok': False, 'error': f'Gaussian 可执行文件不存在：{exe_path}'}), 400

        config = save_config({'gaussian_exe': str(exe_path)})
        return jsonify({'ok': True, 'config': config})

    @app.post('/api/run')
    def run_job():
        payload: dict[str, Any] = request.get_json(silent=True) or {}
        selection = str(payload.get('selection', '')).strip()
        gjf_output_dir = str(payload.get('gjf_output_dir', '')).strip()
        result_output_target = str(payload.get('result_output_target', '')).strip()

        if not selection:
            return jsonify({'ok': False, 'error': '请输入元素序号。'}), 400
        if not gjf_output_dir:
            return jsonify({'ok': False, 'error': '请选择 .gjf 输出目录。'}), 400
        if not result_output_target:
            return jsonify({'ok': False, 'error': '请选择结果输出位置。'}), 400

        config = load_config()
        gaussian_exe = str(config.get('gaussian_exe', '')).strip()
        if not gaussian_exe:
            return jsonify({'ok': False, 'error': '尚未配置 Gaussian 可执行文件路径。'}), 400

        exe_path = Path(gaussian_exe).expanduser().resolve()
        if not exe_path.exists():
            return jsonify({'ok': False, 'error': f'Gaussian 路径无效：{exe_path}'}), 400

        save_config(
            {
                'last_selection': selection,
                'last_gjf_output_dir': gjf_output_dir,
                'last_result_output_target': result_output_target,
            }
        )

        job_id = job_store.create()

        def _log(message: str) -> None:
            job_store.append_log(job_id, message)

        def _progress(step: str, current: int, total: int) -> None:
            job_store.update(
                job_id,
                status='running',
                current_step=step,
                progress_current=current,
                progress_total=total,
                message=step,
            )

        def worker() -> None:
            job_store.update(job_id, status='running', message='任务开始', current_step='初始化')
            try:
                result = run_pipeline(
                    selection=selection,
                    gjf_output_dir=gjf_output_dir,
                    result_output_target=result_output_target,
                    gaussian_exe=gaussian_exe,
                    log=_log,
                    progress=_progress,
                )
                job_store.update(job_id, status='success', message='任务完成', result=result)
            except Exception as exc:  # noqa: BLE001
                job_store.append_log(job_id, f'任务失败：{exc}')
                job_store.update(job_id, status='error', message=str(exc))

        Thread(target=worker, daemon=True).start()
        return jsonify({'ok': True, 'job_id': job_id})

    @app.get('/api/jobs/<job_id>')
    def get_job(job_id: str):
        try:
            snapshot = job_store.snapshot(job_id)
        except KeyError:
            return jsonify({'ok': False, 'error': '任务不存在。'}), 404
        return jsonify({'ok': True, 'job': snapshot})

    return app
