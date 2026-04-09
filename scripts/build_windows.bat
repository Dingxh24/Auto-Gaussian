@echo off
setlocal

cd /d "%~dp0\.."

set BUILD_MODE=%1
if "%BUILD_MODE%"=="" set BUILD_MODE=onedir
if /I "%BUILD_MODE%"=="onefile" set BUILD_MODE=onefile
if /I "%BUILD_MODE%"=="onedir" set BUILD_MODE=onedir

echo [1/3] 安装/更新依赖...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

if errorlevel 1 (
  echo 依赖安装失败。
  exit /b 1
)

echo.
echo [2/3] 以 %BUILD_MODE% 模式构建 exe...
python scripts\build_exe.py --mode %BUILD_MODE%

if errorlevel 1 (
  echo PyInstaller 构建失败。
  exit /b 1
)

echo.
echo [3/3] 构建输出位置：
if /I "%BUILD_MODE%"=="onefile" (
  echo dist\GaussianAtomicWorkbench.exe
) else (
  echo dist\GaussianAtomicWorkbench\GaussianAtomicWorkbench.exe
)
echo.
echo 全部构建完成。
endlocal
