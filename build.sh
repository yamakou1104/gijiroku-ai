#!/bin/bash
set -e

echo "================================================"
echo "  議事録AI ビルドスクリプト (macOS)"
echo "================================================"

# FFmpegの確認
if ! command -v ffmpeg &> /dev/null; then
    echo "[ERROR] FFmpegが見つかりません。brew install ffmpeg を実行してください。"
    exit 1
fi

FFMPEG_PATH=$(which ffmpeg)
FFPROBE_PATH=$(which ffprobe)
FFMPEG_DIR=$(dirname "$FFMPEG_PATH")

echo "FFmpeg found: $FFMPEG_DIR"

# PyInstallerでビルド
pyinstaller --noconfirm \
    --name "GijirokuAI" \
    --windowed \
    --onedir \
    --icon=NONE \
    --add-data "credentials:credentials" \
    --add-binary "$FFMPEG_PATH:." \
    --add-binary "$FFPROBE_PATH:." \
    --hidden-import "pystray._darwin" \
    --hidden-import "plyer.platforms.macosx.notification" \
    --hidden-import "google.auth.transport.requests" \
    main.py

echo ""
echo "================================================"
echo "  ビルド完了！"
echo "  出力先: dist/GijirokuAI/GijirokuAI"
echo "================================================"
echo ""
echo "配布する前に credentials/ フォルダに"
echo "OAuth認証情報を配置してください。"
echo "（credentials/README.md を参照）"
