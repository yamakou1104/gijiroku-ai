#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PATH="$HOME/Desktop/GijirokuAI.app"
CONTENTS="$APP_PATH/Contents"
MACOS_DIR="$CONTENTS/MacOS"

echo "議事録AI デスクトップショートカット作成"
echo "========================================"

# Remove old app if exists
if [ -d "$APP_PATH" ]; then
    echo "既存のアプリを削除中..."
    rm -rf "$APP_PATH"
fi

# Create directory structure
mkdir -p "$MACOS_DIR"

# Write Info.plist
cat > "$CONTENTS/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>GijirokuAI</string>
    <key>CFBundleDisplayName</key>
    <string>議事録AI</string>
    <key>CFBundleExecutable</key>
    <string>GijirokuAI</string>
    <key>CFBundleIdentifier</key>
    <string>com.gijiroku-ai.app</string>
    <key>CFBundleVersion</key>
    <string>0.1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
</dict>
</plist>
PLIST

# Write launcher script
cat > "$MACOS_DIR/GijirokuAI" << LAUNCHER
#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:\$PATH"
cd "$SCRIPT_DIR" || exit 1
exec /usr/bin/python3 main.py --gui
LAUNCHER

chmod +x "$MACOS_DIR/GijirokuAI"

echo ""
echo "作成完了: $APP_PATH"
echo ""
echo "デスクトップの GijirokuAI をダブルクリックで起動できます。"
echo "Dockにドラッグして固定することも可能です。"
