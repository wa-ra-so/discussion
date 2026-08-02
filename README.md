# Discussion System - 食べログ営業向け商談解析システム

文字起こし済みの商談テキストを自動解析し、ディスカッションシートの項目を構造化データ（JSON）として保存・管理するシステムです。CLI と Web UI の両方から利用できます。

## 概要

このシステムは、食べログ営業が店舗との商談中に得た情報を以下の流れで効率化します：

```
文字起こし済みテキスト（音声認識アプリ等で事前に作成）
    ↓
Claude API（テキスト解析 + ディスカッション項目への自動マッピング）
    ↓
法人名 → 店舗名 の階層に整理して蓄積（SQLite）
    ↓
JSON 形式の構造化記録
    ↓
法人カルテ生成（CLI: Markdown/JSON、Web UI: ブラウザ表示）
```

音声認識（文字起こし）自体はこのシステムでは行いません。既に文字起こし済みのテキスト（スマホの録音アプリの文字起こし機能や他の文字起こしツールの出力など）を入力として使う前提です。

## 主な機能

- ✅ JSON スキーマ・Pydantic モデル（ディスカッション6セクション全対応）
- ✅ Claude API によるテキストからの自動抽出
- ✅ 法人（corporate）→ 店舗（company）の階層管理、法人カルテで店舗ごとの課題有無を一覧化
- ✅ SQLite への蓄積・企業別検索・法人カルテ生成
- ✅ CLI（Typer）と Web UI（Next.js + HeroUI）の両対応
- ✅ FastAPI バックエンド（レート制限設定済み）。本番はフロントエンドの静的ビルドも同一プロセスから配信し、CORSの設定ミスが起きないようにしている

## ディスカッション項目

システムが自動抽出・管理する6つのセクション：

1. **採用・人手** - スタッフ構成、採用課題、求人施策
2. **集客・売上** - 客単価、席稼働率、客層、売上施策
3. **予約・業務効率** - 予約システム、発注業務、オペレーション課題
4. **インバウンド集客** - 外国人客対応、多言語対応状況
5. **優先課題** - 複数の課題を優先度付けして合意
6. **DXソリューション** - 食べログの提案ソリューション

## ディレクトリ構成

```
discussion/
├── pyproject.toml / requirements.txt   # Python 依存関係
├── .env.example                        # 環境変数テンプレート
├── Dockerfile / fly.toml               # デプロイ設定（フロント+バックエンド一体）
│
├── schema/
│   ├── discussion_schema.json          # JSON スキーマ定義（マスター）
│   └── models.py                       # Pydantic モデル
│
├── src/
│   ├── main.py                         # CLI エントリーポイント
│   ├── config.py                       # 設定管理（環境変数）
│   ├── api/main.py                     # FastAPI バックエンド（フロント静的配信も兼ねる）
│   ├── core/                           # Claude API・パイプライン
│   ├── storage/sqlite_manager.py       # SQLite 蓄積・検索
│   └── commands/                       # CLI コマンド実装
│
├── web/                                # Next.js + HeroUI フロントエンド（静的書き出し）
│   └── src/
│       ├── app/page.tsx                # メイン画面（タブ切り替え）
│       ├── components/                 # Process/List/Search/Card パネル
│       └── lib/                        # API クライアント・型定義
│
└── data/                                # JSON記録・SQLite（gitignore対象）
```

## セットアップ

### 前提条件
- Python 3.10 以上
- Node.js 20 以上（Web UI を使う場合）
- Anthropic API キー

### バックエンド

```bash
cd discussion
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# .env を編集して ANTHROPIC_API_KEY を設定
```

### フロントエンド（Web UI を使う場合）

```bash
cd discussion/web
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

## 使用方法

### Web UI（推奨・ローカル開発時）

**ターミナル1: バックエンド**
```bash
python -m uvicorn src.api.main:app --reload --port 8000
```
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

**ターミナル2: フロントエンド**
```bash
cd web
npm run dev
```
- UI: http://localhost:3000

画面は4つのタブで構成されています:
- **テキスト解析** — 文字起こし済みテキストを貼り付けて自動解析
- **一覧** — 登録済み法人・店舗・商談履歴の一覧
- **検索** — 優先課題をキーワード横断検索
- **法人カルテ** — 法人・店舗別の商談履歴を集約表示（法人カルテでは店舗ごとの課題有無も一覧化）

本番環境では Fly.io 1つだけで完結します。Docker ビルド時に Next.js を静的書き出しし、FastAPI が同一オリジンでフロントエンドとAPIの両方を配信するため、別サービス間のCORS設定は不要です。

### CLI

```bash
# 文字起こし済みテキストを処理（transcript.txt は文字起こし済みテキストのファイル）
python -m src.main process transcript.txt --company "レストランA" --contact "山田太郎"

# 商談記録の一覧表示
python -m src.main list-meetings
python -m src.main list-meetings --company "レストランA"

# 課題をキーワード検索
python -m src.main search "人手不足"

# 法人カルテを生成
python -m src.main card "レストランA" --format markdown
python -m src.main card "レストランA" --format json --output card.json

# ヘルプ
python -m src.main --help
```

## JSON スキーマ

抽出されたディスカッション記録は以下の構造で JSON として保存されます：

```json
{
  "meeting_id": "20240131_1400_example_restaurant",
  "company_info": {
    "name": "レストランA",
    "corporate_name": "株式会社レストランA",
    "contact_name": "山田太郎",
    "contact_email": "yamada@example.com",
    "date": "2024-01-31T14:00:00"
  },
  "discussions": {
    "recruitment": {
      "assumed_issues": "人手不足で営業時間短縮を余儀なくされている",
      "current_staff": { "employees": 1, "part_time": 2 },
      "ideal_staff": { "employees": 2, "part_time": 3 }
    },
    "sales": { "..." : "..." },
    "booking_efficiency": { "..." : "..." },
    "inbound": { "..." : "..." }
  },
  "priority_issues": [
    { "category": "recruitment", "issue": "求人を出しても応募が全く来ない", "priority": 5 }
  ],
  "dx_solutions": { "..." : "..." },
  "next_steps": { "..." : "..." },
  "confidence_score": 0.85,
  "created_at": "2024-01-31T14:05:00",
  "summary": "..."
}
```

詳細は `schema/discussion_schema.json` を参照。

## セキュリティ

- `ANTHROPIC_API_KEY` はサーバー側のみで使用し、フロントエンドには一切露出しません
- レート制限: `/api/process` は20回/分、その他は30回/分（IPアドレス単位）
- 文字起こしテキストは10文字未満だと拒否されます

## トラブルシューティング

**API キーエラー**: `.env` ファイルで `ANTHROPIC_API_KEY` を設定してください。

**フロントエンドが API に接続できない（ローカル開発時）**: `web/.env.local` の `NEXT_PUBLIC_API_URL` がバックエンドの起動アドレスと一致しているか確認してください。本番ビルドでは同一オリジン配信のため空文字列（相対パス）を使います。

## テスト

```bash
pytest
pytest --cov=src
```

## ライセンス

MIT License

## お問い合わせ

Tabelog Sales Team - souta55908@gmail.com
