# デプロイ手順

このプロジェクトは以下の2つを別々にデプロイします。

- **バックエンド（FastAPI + Whisper + SQLite）** → Fly.io（無料枠あり）
- **フロントエンド（Next.js + HeroUI）** → **GitHub Pages**（無料・GitHub Actionsで自動デプロイ）または Vercel

> **注意**: GitHub Pages は静的ファイル（HTML/CSS/JS）しか配信できません。Python サーバー・Whisper・SQLite を動かすバックエンドは GitHub Pages では動作しないため、フロントエンドだけを GitHub Pages に置き、バックエンドは Fly.io など何らかのサーバーで動かす必要があります。

---

## 1. バックエンド（Fly.io）

### 事前準備

```bash
curl -L https://fly.io/install.sh | sh
flyctl auth login
```

### 初回デプロイ

リポジトリのルート（`discussion/`）で実行します。`fly.toml` と `Dockerfile` は既に用意済みです。

```bash
flyctl launch --name discussion-api --no-deploy
# 既存の fly.toml を使うか聞かれたら "yes"

# 永続ボリューム作成（SQLite データを保持するため）
flyctl volumes create discussion_data --size 1 --region nrt

# APIキーをシークレットとして設定（.env の値は絶対にコミットしない）
flyctl secrets set ANTHROPIC_API_KEY=sk-ant-xxxxx

# デプロイ
flyctl deploy
```

デプロイ後、`https://discussion-api.fly.dev` でAPIが公開されます。

### 動作確認

```bash
curl https://discussion-api.fly.dev/api/health
```

### CORS の許可オリジンを更新

`fly.toml` の `CORS_ORIGINS` を実際のフロントエンドURLに変更してから再デプロイ（GitHub Pages の場合はプロジェクトページのURL、例: `https://wa-ra-so.github.io`）:

```toml
[env]
  CORS_ORIGINS = "https://wa-ra-so.github.io"
```

```bash
flyctl deploy
```

---

## 2. フロントエンド（GitHub Pages — 推奨）

`web/` を静的サイトとしてビルドし、`.github/workflows/deploy-pages.yml` で自動デプロイします。設定済みのファイルは以下の通りです:

- `web/next.config.ts` — `output: "export"` で静的エクスポート。`GITHUB_PAGES=true` のときだけ `basePath`/`assetPrefix` を `/discussion`（リポジトリ名）に設定
- `.github/workflows/deploy-pages.yml` — push 時に `web/` をビルドして GitHub Pages にデプロイ

### 手順

1. **リポジトリ設定を有効化**
   GitHub リポジトリ → Settings → Pages → Source を **GitHub Actions** に設定

2. **バックエンドURLを Variables に登録**
   Settings → Secrets and variables → Actions → Variables タブ → New repository variable

   ```
   Name:  NEXT_PUBLIC_API_URL
   Value: https://discussion-api.fly.dev
   ```

3. **`main` ブランチに push（または手動実行）**

   ```bash
   git push origin main
   ```

   もしくは Actions タブから `Deploy Frontend to GitHub Pages` を `workflow_dispatch` で手動実行。

4. **公開URLを確認**

   `https://wa-ra-so.github.io/discussion/` でアクセスできます（リポジトリ名が `discussion` でない場合は `web/next.config.ts` の `repoName` を実際のリポジトリ名に合わせてください）。

### ローカルで GitHub Pages 相当のビルドを試す

```bash
cd web
GITHUB_PAGES=true NEXT_PUBLIC_API_URL=https://discussion-api.fly.dev npm run build
# web/out/ に静的ファイルが生成される
npx serve out  # or any static file server
```

---

## 2b. フロントエンド（Vercel — 代替案）

GitHub Pages の代わりに Vercel を使うことも可能です（`web/vercel.json` を用意済み）。

`web/` ディレクトリが Next.js プロジェクトです。

### Vercel CLI でのデプロイ

```bash
cd web
npm install -g vercel
vercel login
vercel
```

質問には以下のように答えます:
- Set up and deploy: `Y`
- Link to existing project: プロジェクトによる
- Root directory: そのまま（`web/` 内で実行しているため）

### 環境変数を設定

Vercel ダッシュボード → Project Settings → Environment Variables:

```
NEXT_PUBLIC_API_URL = https://discussion-api.fly.dev
```

設定後、再デプロイ:

```bash
vercel --prod
```

### GitHub 連携でのデプロイ（推奨）

1. https://vercel.com/new でリポジトリをインポート
2. **Root Directory** を `web` に設定（重要 — モノレポ構成のため）
3. 環境変数 `NEXT_PUBLIC_API_URL` を設定
4. Deploy をクリック

以降、`main`（または対象ブランチ）への push で自動デプロイされます。

---

## 3. セキュリティチェックリスト

- [x] `ANTHROPIC_API_KEY` はサーバー側のシークレットのみに保存（フロントエンドに一切露出しない）
- [x] CORS は許可したオリジンのみ（本番URLに更新すること）
- [x] レート制限実装済み（`/api/process`: 5回/分、その他: 30回/分、IPアドレス単位）
- [x] アップロードファイルの形式・サイズ検証（100MB上限）
- [x] Fly.io / Vercel いずれも自動的に HTTPS を提供

---

## 4. ローカル動作確認（デプロイ前の確認用）

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

---

## 5. コスト試算

| 項目 | 月額 |
|---|---|
| Vercel（フロントエンド、Hobbyプラン） | $0 |
| Fly.io（バックエンド、shared-cpu-1x 2GB） | 無料枠内（$0〜数ドル） |
| Anthropic API（Claude、従量課金） | 使用量に応じる |

Whisper はサーバー内でモデルをロードして実行するため追加のAPI費用は発生しません（計算リソースのみ）。
