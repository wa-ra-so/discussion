# Discussion System - 食べログ営業向け商談解析システム

商談音声を自動解析し、ディスカッションシートの項目を構造化データ（JSON）として保存・管理するシステムです。CLI と Web UI の両方から利用できます。

## 概要

このシステムは、食べログ営業が店舗との商談中に得た情報を以下の流れで効率化します：

```
商談音声 (MP3/WAV)
    ↓
Whisper (自動音声認識)
    ↓
Claude API (テキスト解析 + ディスカッション項目への自動マッピング)
    ↓
JSON 形式の構造化記録 + SQLite への蓄積
    ↓
法人カルテ生成（CLI: Markdown/JSON、Web UI: ブラウザ表示）
```

## 主な機能

- ✅ JSON スキーマ・Pydantic モデル（ディスカッション6セクション全対応）
- ✅ 音声認識（Whisper）+ テキスト解析（Claude API）による自動抽出
- ✅ SQLite への蓄積・企業別検索・法人カルテ生成
- ✅ CLI（Typer）と Web UI（Next.js + HeroUI）の両対応
- ✅ FastAPI バックエンド（レート制限・CORS 設定済み）

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
├── Dockerfile / fly.toml               # バックエンドのデプロイ設定
├── DEPLOYMENT.md                       # デプロイ手順（Fly.io + Vercel）
│
├── schema/
│   ├── discussion_schema.json          # JSON スキーマ定義（マスター）
│   └── models.py                       # Pydantic モデル
│
├── src/
│   ├── main.py                         # CLI エントリーポイント
│   ├── config.py                       # 設定管理（環境変数）
│   ├── api/main.py                     # FastAPI バックエンド
│   ├── core/                           # Whisper・Claude API・パイプライン
│   ├── storage/sqlite_manager.py       # SQLite 蓄積・検索
│   └── commands/                       # CLI コマンド実装
│
├── web/                                # Next.js + HeroUI フロントエンド
│   └── src/
│       ├── app/page.tsx                # メイン画面（タブ切り替え）
│       ├── components/                 # Process/List/Search/Card パネル
│       └── lib/                        # API クライアント・型定義
│
└── data/                                # 音声・JSON記録・SQLite（gitignore対象）
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

### Web UI（推奨）

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
- **音声処理** — 音声ファイルをアップロードして自動解析
- **一覧** — 登録済み企業・商談履歴の一覧
- **検索** — 優先課題をキーワード横断検索
- **法人カルテ** — 企業別の商談履歴を集約表示

本番デプロイの手順は `DEPLOYMENT.md` を参照してください（Fly.io + Vercel、無料枠で構築可能）。

### CLI

```bash
# 商談音声を処理
python -m src.main process meeting.wav --company "レストランA" --contact "山田太郎"

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
- CORS は許可オリジンのみ（`CORS_ORIGINS` 環境変数で設定）
- レート制限: `/api/process` は5回/分、その他は30回/分（IPアドレス単位）
- アップロードファイルは形式・サイズ（100MB上限）を検証

## トラブルシューティング

**API キーエラー**: `.env` ファイルで `ANTHROPIC_API_KEY` を設定してください。

**フロントエンドが API に接続できない**: `web/.env.local` の `NEXT_PUBLIC_API_URL` がバックエンドの起動アドレスと一致しているか確認してください。

**音声ファイルが見つからない**: ファイルパスが正しいか、対応形式（MP3/WAV/M4A/FLAC/OGG）か確認してください。

## テスト

```bash
pytest
pytest --cov=src
```

## ライセンス

MIT License

## お問い合わせ

Tabelog Sales Team - souta55908@gmail.com
