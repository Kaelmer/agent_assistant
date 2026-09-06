@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Agent 助手一键启动
echo   地址: http://127.0.0.1:8000
echo   首次启动需 10~20 秒加载模型,请耐心等待
echo ============================================
echo.

rem 后台延时打开浏览器(等模型加载完、端口就绪)
start "" /min cmd /c "timeout /t 12 /nobreak >nul & start http://127.0.0.1:8000"

rem 用项目虚拟环境启动服务(前台运行,关闭本窗口即停止)
".venv\Scripts\python.exe" -m uvicorn src.app:app --host 127.0.0.1 --port 8000

echo.
echo 服务已停止。
pause
