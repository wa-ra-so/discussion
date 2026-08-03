# デプロイ手順

このプロジェクトは **Fly.io 1つだけ**でデプロイします。Docker ビルド時に Next.js フロントエンドを静的書き出しし、FastAPI がそれをAPIと同じオリジンから配信するため、フロントエンド用の別サービス（GitHub Pages / Vercel）は不要です。CORSの設定ミスによる接続エラーも発生しません。

> **現在の状態**: Fly.io（GitHub 連携の Launch 機能）に既にデプロイ済みです。
> アプリ名は `discussion-xcctgw`、公開URLは `https://discussion-xcctgw.fly.dev` です。
> 永続ボリューム（`discussion_data`, 1GB, 東京リージョン）と `ANTHROPIC_API_KEY` シークレットも設定済みです。

---

## 1. 事前準備

```bash
curl -L https://fly.io/install.sh | sh
flyctl auth login
```

## 2. 初回デプロイ

リポジトリのルート（`discussion/`）で実行します。`fly.toml` と `Dockerfile` は既に用意済みです。

```bash
flyctl launch --no-deploy
# 既存の fly.toml を使うか聞かれたら "yes"

# 永続ボリューム作成（SQLite データを保持するため。既に作成済みなら不要）
flyctl volumes create discussion_data --size 1 --region nrt

# APIキーをシークレットとして設定（.env の値は絶対にコミットしない）
flyctl secrets set ANTHROPIC_API_KEY=sk-ant-xxxxx

# デプロイ
flyctl deploy
```

デプロイ後、`https://discussion-xcctgw.fly.dev` でアプリ（フロントエンド + API）が公開されます。

## 3. 動作確認

```bash
curl https://discussion-xcctgw.fly.dev/api/health
```

ブラウザで `https://discussion-xcctgw.fly.dev` を開くと、そのままWeb UIが表示されます。

## 4. 再デプロイ

コードを変更したら以下だけで反映されます:

```bash
flyctl deploy
```

GitHub と連携している場合は、対象ブランチに push した後、Fly.io ダッシュボードから再デプロイを実行してください（自動デプロイが設定されていない場合）。

### Secrets の確認

Fly.io の Secrets（`fly secrets list` またはダッシュボードの Secrets タブ）に、`fly.toml` の `[env]` と重複するキーが残っていないか確認してください。Secrets は `[env]` より優先されるため、古い値が残っていると意図しない設定で動いてしまいます。この構成では `CORS_ORIGINS` の Secret は不要です（同一オリジン配信のため）。

---

## 5. セキュリティチェックリスト

- [x] `ANTHROPIC_API_KEY` はサーバー側のシークレットのみに保存（フロントエンドに一切露出しない）
- [x] レート制限実装済み（`/api/process`: 20回/分、その他: 30回/分、IPアドレス単位）
- [x] 文字起こしテキストは10文字未満だと拒否
- [x] Fly.io が自動的に HTTPS を提供

---

## 6. ローカル動作確認（デプロイ前の確認用）

**個別に起動する場合（開発しやすい）:**

```bash
# ターミナル1: バックエンド
cd discussion
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # ANTHROPIC_API_KEY を設定
python -m uvicorn src.api.main:app --reload --port 8000

# ターミナル2: フロントエンド
cd discussion/web
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

http://localhost:3000 をブラウザで開いて動作確認してください。

**本番と同じ構成（同一オリジン配信）を試す場合:**

```bash
cd discussion/web
NEXT_PUBLIC_API_URL="" npm run build   # web/out/ に静的ファイルが生成される
cd ..
WEB_DIST_DIR=web/web/out python -m uvicorn src.api.main:app --port 8000
```

http://localhost:8000 を開くと、フロントエンドとAPIが同じポートから配信されます。

---

## 7. コスト試算

| 項目 | 月額 |
|---|---|
| Fly.io（shared-cpu-1x 4GB、Whisperモデルを含む） | 数ドル〜（メモリ量に応じて課金） |
| Anthropic API（Claude、従量課金） | 使用量に応じる |

Whisper はサーバー内でモデルをロードして実行するため、追加のAPI費用は発生しません（計算リソースのみ）。音声処理は数十秒〜数分かかるため非同期ジョブ+ポーリング方式で行い、テキスト入力（数秒で完了）とは別経路（`/api/process-audio`）で処理しています。
