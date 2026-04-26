# OAuth認証情報の設定（開発者向け）

配布用の .exe をビルドする前に、以下のOAuth認証情報を設定してください。

## Google Drive

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成（例: 「議事録AI」）
3. 「APIとサービス」→「ライブラリ」→「Google Drive API」を有効化
4. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuthクライアントID」
5. アプリケーションの種類: 「デスクトップアプリ」
6. 作成後、JSONをダウンロード
7. ダウンロードしたファイルを `credentials/google_client_secrets.json` として保存

### OAuth同意画面の設定
- ユーザーの種類: 「外部」
- アプリ名: 「議事録AI」
- スコープ: `https://www.googleapis.com/auth/drive.file`
- テストユーザーに配布先のGmailアドレスを追加（本番公開前）

## OneDrive

1. [Azure Portal](https://portal.azure.com/) → 「Azure Active Directory」→「アプリの登録」
2. 「新規登録」
   - 名前: 「議事録AI」
   - サポートされるアカウントの種類: 「個人用Microsoftアカウント」
   - リダイレクトURI: 不要（デバイスコードフロー使用）
3. 登録後、「概要」ページの「アプリケーション (クライアント) ID」をコピー
4. `credentials/onedrive_config.json` を作成:

```json
{
  "client_id": "ここにクライアントIDを貼り付け"
}
```

## 確認

設定完了後、以下のファイルが存在することを確認:
- `credentials/google_client_secrets.json`
- `credentials/onedrive_config.json`
