# 議事録AI

会議を自動で録音・文字起こし・議事録生成するデスクトップアプリケーション。

## 主な機能

- **会議の自動検出** -- Zoom / Microsoft Teams / Google Meet のウィンドウを検出し、録音を自動開始・停止
- **Gemini による文字起こし** -- Google Gemini API を使用して音声ファイルを高精度にテキスト化
- **議事録の自動生成** -- 文字起こし結果から構造化された議事録を自動で作成
- **クラウドアップロード** -- Google Drive または OneDrive への自動アップロードに対応
- **macOS / Windows 対応** -- 両プラットフォームでの動作をサポート
- **対面 / オンライン両対応** -- マイク録音（対面会議）と画面録画+音声録音（オンライン会議）の2モード

## 動作要件

- Python 3.9 以上
- FFmpeg（録音・録画に必要）
- Gemini API キー（[Google AI Studio](https://aistudio.google.com/) で取得）
- macOS の場合: BlackHole（オンライン会議のシステムオーディオキャプチャに必要、`brew install blackhole-2ch`）

## インストール

```bash
git clone https://github.com/your-repo/gijiroku-ai.git
cd gijiroku-ai
pip install -r requirements.txt
```

`.env` ファイルを作成し、API キーを設定する。

```bash
cp .env.example .env
```

`.env` を編集して `GEMINI_API_KEY` に取得した API キーを記入する。

```
GEMINI_API_KEY=your_api_key_here
```

### FFmpeg のインストール

**macOS:**

```bash
brew install ffmpeg
```

**Windows:**

[FFmpeg 公式サイト](https://ffmpeg.org/download.html)からダウンロードし、PATH に追加する。

## 初回セットアップ

アプリを起動すると、セットアップウィザードが自動的に表示される。ウィザードでは以下の設定を行う。

1. FFmpeg の検出確認
2. 録音デバイスの選択
3. クラウドストレージの設定（Google Drive / OneDrive / なし）
4. OAuth 認証（クラウドストレージを選択した場合）

## 使い方

### GUI モード

ウィンドウ付きの GUI で録音操作を行う。

```bash
python main.py --gui
```

### トレイモード

システムトレイ（macOS ではメニューバー）に常駐し、会議を自動検出して録音する。

```bash
python main.py
```

### デスクトップショートカット（macOS）

macOS の場合、デスクトップにアプリケーションショートカットを作成できる。

```bash
bash create_shortcut.sh
```

`~/Desktop/GijirokuAI.app` が作成され、ダブルクリックで GUI モードが起動する。Dock にドラッグして固定することも可能。

## 設定

### API キー（.env）

`.env` ファイルで管理される設定項目:

| 変数名 | 説明 |
|--------|------|
| `GEMINI_API_KEY` | Gemini API キー（必須） |
| `GIJIROKU_ENCRYPTION_KEY` | OAuth トークン暗号化キー（初回起動時に自動生成） |

### アプリケーション設定（config.json）

`~/.gijiroku-ai/config.json` に保存される設定項目:

- 録音モード（対面 / オンライン）
- 録音デバイス
- アップロード先（Google Drive / OneDrive / なし）
- 出力ディレクトリ

設定はセットアップウィザードまたは GUI から変更できる。

## セキュリティ

- **API キー**: `.env` ファイルで管理し、`config.json` には保存しない。`.env` は `.gitignore` に含まれている
- **OAuth トークン**: Fernet 暗号化で保護される。暗号化キーは `.env` の `GIJIROKU_ENCRYPTION_KEY` に保存され、初回起動時に自動生成される
- **クレデンシャルファイル**: `credentials/` ディレクトリ内の OAuth クライアントシークレットはリポジトリに含めないこと

## 開発

### プロジェクト構成

```
gijiroku-ai/
  main.py              # エントリポイント
  config.py            # 設定管理
  pipeline.py          # 録音→文字起こし→議事録生成→アップロードのパイプライン
  exceptions.py        # カスタム例外
  recorder/            # 録音・録画モジュール（FFmpeg）
  transcriber/         # 文字起こしモジュール（Gemini API）
  generator/           # 議事録生成モジュール（Gemini API）
  uploader/            # クラウドアップロード（Google Drive / OneDrive）
  tray/                # システムトレイアプリ（会議自動検出）
  ui/                  # GUI（Tkinter）
  utils/               # ユーティリティ（暗号化、通知、リトライ等）
  tests/               # テスト
  credentials/         # OAuth クライアントシークレット（gitignore対象）
```

### テストの実行

```bash
python -m pytest tests/ -v
```

### 開発用インストール

```bash
pip install -e ".[dev]"
```

## 免責事項

本ソフトウェアは現状有姿（AS IS）で提供され、明示・黙示を問わず、いかなる種類の保証も行いません。

- **録音に関する責任**: 会議の録音にあたっては、参加者全員の同意を事前に得てください。無断録音は法律で禁止されている場合があります。録音の合法性については利用者自身の責任で確認してください
- **データの取り扱い**: 録音データ、文字起こしテキスト、議事録には機密情報が含まれる可能性があります。これらのデータの保管・共有・削除は利用者の責任で適切に管理してください
- **外部サービス**: 本ソフトウェアは Google Gemini API、Google Drive API、Microsoft OneDrive API 等の外部サービスを利用します。各サービスの利用規約は利用者自身で遵守してください。API の利用料金、サービスの変更・停止等について、本ソフトウェアの開発者は一切の責任を負いません
- **損害の免責**: 本ソフトウェアの使用により生じたいかなる損害（データの損失、録音の失敗、情報漏洩等を含むがこれに限らない）についても、開発者は一切の責任を負いません

本ソフトウェアの利用は、全て利用者自身の責任において行ってください。

## ライセンス

MIT License
