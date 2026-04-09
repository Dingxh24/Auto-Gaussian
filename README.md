# Gaussian Atomic Workbench

一个将 `.gjf` 生成、Gaussian 批量计算、以及 `.out/.log` 结果汇总合并为单一桌面程序的项目。

## 功能概览

- 输入原子序数范围，例如：`1-3,5,8`
- 自动为中性态、正离子、负离子生成 `.gjf` 文件
- 调用用户本机安装的 Gaussian 可执行文件进行批量计算
- 自动读取 `.out` / `.log` 中最后一个 `SCF Done:` 能量
- 输出 Excel 与 CSV 汇总表
- 提供 **Flask + pywebview** 桌面窗口，无需用户手动执行脚本
- 提供 Windows 打包脚本（`PyInstaller`）

---

## 仓库结构

```text
.
├─ gaussian_atomic_app/
│  ├─ core/
│  │  ├─ analyzer.py
│  │  ├─ atomic_data.py
│  │  ├─ gaussian_runner.py
│  │  ├─ gjf_generator.py
│  │  └─ workflow.py
│  ├─ static/
│  │  └─ style.css
│  ├─ templates/
│  │  └─ index.html
│  ├─ config.py
│  ├─ desktop.py
│  ├─ jobs.py
│  └─ web.py
├─ build/
│  └─ windows/
│     └─ GaussianAtomicWorkbench.spec
├─ scripts/
│  └─ build_windows.bat
├─ main.py
├─ requirements.txt
├─ .gitignore
└─ LICENSE
```

---

## 运行方式（源码）

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动桌面程序

```bash
python main.py
```

首次运行后，如果尚未配置 Gaussian 路径，请在界面顶部先选择你的 `g16.exe` / `g09.exe`。

> 如遇到 WebView2 相关报错导致界面异常，可尝试切换 pywebview 后端（例如）：
> - PowerShell：`$env:GAW_WEBVIEW_GUI="mshtml"; python main.py`

---

## 使用说明

界面中一共需要填写 3 项：

1. **元素序号**
   - 支持格式：`1,2,3`
   - 支持范围：`1-3`
   - 支持混合：`1-3,5,8`

2. **.gjf 文件输出目录**
   - 程序会在该目录下生成：
     - `H+.gjf`
     - `H.gjf`
     - `H-.gjf`
     - 等等

3. **最终结果输出位置**
   - 可以直接指定 `.xlsx` 文件路径，例如：
     - `D:\result\原子能性质汇总.xlsx`
   - 程序也会同步写出同名 `.csv`

程序执行流程：

1. 解析元素序号
2. 生成 `.gjf`
3. 调用 Gaussian 执行计算
4. 搜索同目录中的 `.out/.log`
5. 提取 `SCF Done:` 的最后一个能量值
6. 计算：
   - 第一电离能
   - 电子亲和能
   - 化学势
   - Mulliken 电负性
7. 输出 Excel / CSV

---

## Windows 打包

### 方式一：直接执行打包脚本

```bat
scripts\build_windows.bat
```

也可以打包为单文件 exe：

```bat
scripts\build_windows.bat onefile
```

该脚本会尝试：

1. 安装依赖
2. 使用 `PyInstaller` 构建 exe（默认 `onedir`，可选 `onefile`）

### 方式二：手动构建

#### 1. 先构建程序目录

```bash
pyinstaller build/windows/GaussianAtomicWorkbench.spec --noconfirm
```

#### 2. 构建单文件 exe（可选）

```bash
python scripts/build_exe.py --mode onefile
```

---

## 兼容性设计

### 当前重点支持

- Windows 10 / 11
- Python 3.10+
- Gaussian 已在本机安装

### 同时保留的跨平台能力

本项目界面层基于 Flask + pywebview，程序主体与路径解析逻辑均使用 `pathlib`，因此源码本身仍然保持较好的跨平台适配性。只是当前提供的打包脚本以 Windows 为主。

---

## 说明

### 为什么分析 `.out` 和 `.log`

你原来的分析脚本只扫描 `.out`。为了适配不同 Gaussian 运行习惯，这个版本会同时识别 `.out` 和 `.log`，并优先使用最近更新的结果文件。

### 为什么不强依赖系统 PATH

程序本体始终使用 **显式的 Gaussian 可执行文件路径** 来调用 Gaussian（并写入用户配置文件），因此更稳定，也更容易排查路径问题。

---

## 开发建议

如果后续还要扩展，可以优先考虑：

- 增加计算过程日志导出
- 增加任务队列 / 批量任务历史
- 增加失败任务自动重跑
- 增加更多 Gaussian 路由模板与方法设置
- 增加 Gaussian 版本检测

---

## 许可证

MIT
