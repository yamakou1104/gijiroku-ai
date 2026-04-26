@echo off
echo ================================================
echo   議事録AI ビルドスクリプト
echo ================================================

REM FFmpegの場所を確認
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] FFmpegが見つかりません。PATHにFFmpegを追加してください。
    exit /b 1
)

REM FFmpegのパスを取得
for /f "delims=" %%i in ('where ffmpeg') do set FFMPEG_PATH=%%i
for %%i in ("%FFMPEG_PATH%") do set FFMPEG_DIR=%%~dpi

echo FFmpeg found: %FFMPEG_DIR%

REM PyInstallerでビルド
pyinstaller --noconfirm ^
    --name "GijirokuAI" ^
    --windowed ^
    --onedir ^
    --icon=NONE ^
    --add-data "credentials;credentials" ^
    --add-binary "%FFMPEG_DIR%ffmpeg.exe;." ^
    --add-binary "%FFMPEG_DIR%ffprobe.exe;." ^
    --hidden-import "pystray._win32" ^
    --hidden-import "plyer.platforms.win.notification" ^
    --hidden-import "google.auth.transport.requests" ^
    --hidden-import "win32gui" ^
    --hidden-import "win32api" ^
    --hidden-import "win32con" ^
    main.py

if %errorlevel% neq 0 (
    echo [ERROR] ビルドに失敗しました。
    exit /b 1
)

echo.
echo ================================================
echo   ビルド完了！
echo   出力先: dist\GijirokuAI\GijirokuAI.exe
echo ================================================
echo.
echo 配布する前に credentials/ フォルダに
echo OAuth認証情報を配置してください。
echo （credentials/README.md を参照）
