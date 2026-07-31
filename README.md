# Discussion System - 食べログ営業向け商談解析システム

商談音声を自動解析し、ディスカッションシートの項目を構造化データ（JSON）として保存・管理するシステムです。

## 概要

このシステムは、食べログ営業が店舗との商談中に得た情報を以下の流れで効率化します：

```
商談音声 (MP3/WAV)
    ↓
Whisper (自動音声認識)
    ↓
Claude API (テキスト解析 + ディスカッション項目への自動マッピング)
    ↓
JSON 形式の構造化記録
    ↓
法人カルテ生成・蓄積
```

## 主な機能

### Phase 1（現在実装済み）
- ✅ JSON スキーマ定義（6つのディスカッション項目）
- ✅ Pydantic データモデル
- ✅ CLI 基本構造
- ✅ プロジェクト設定・ロギング

### Phase 2（実装予定）
- 🔄 音声認識パイプライン（Whisper）
- 🔄 テキスト解析（Claude API）
- 🔄 自動ディスカッション項目抽出
- 🔄 信頼度スコア付与

### Phase 3（実装予定）
- 🔄 SQLite データベース設計
- 🔄 商談蓄積・検索機能
- 🔄 法人カルテ生成（JSON/Markdown/PDF）
- 🔄 複数商談の統合表示

## ディスカッション項目

システムが自動抽出・管理する6つのセクション：

1. **採用・人手** - スタッフ構成、採用課題、求人施策
2. **集客・売上** - 客単価、席稼働率、客層、売上施策
3. **予約・業務効率** - 予約システム、発注業務、オペレーション課題
4. **インバウンド集客** - 外国人客対応、多言語対応状況
5. **優先課題** - 複数の課題を優先度付けして合意
6. **DXソリューション** - 食べログの提案ソリューション

## インストール

### 前提条件
- Python 3.10 以上
- Anthropic API キー

### セットアップ

```bash
# リポジトリをクローン
git clone <repository_url>
cd discussion

# 仮想環境を作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt

# 環境変数を設定
cp .env.example .env
# .env を編集して ANTHROPIC_API_KEY を設定

# プロジェクトを初期化
python -m src.main init
```

## 使用方法

### 基本コマンド

#### 1. 商談音声を処理
```bash
python -m src.main process meeting.wav \
  --company "レストランA" \
  --contact "山田太郎" \
  --notes "初回面談"
```

#### 2. 商談記録の一覧表示
```bash
python -m src.main list-meetings --limit 20
python -m src.main list-meetings --company "レストランA"
```

#### 3. 商談記録を検索
```bash
python -m src.main search "人手不足" --field issue
python -m src.main search "予約効率" --field category
```

#### 4. 法人カルテを生成
```bash
python -m src.main card "レストランA" --format markdown
python -m src.main card "レストランA" --format json
python -m src.main card "レストランA" --format pdf
```

#### 5. データをエクスポート
```bash
python -m src.main export "レストランA" --output result.json
```

### CLI ヘルプ
```bash
python -m src.main --help
python -m src.main process --help
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
      "ideal_staff": { "employees": 2, "part_time": 3 },
      ...
    },
    "sales": { ... },
    "booking_efficiency": { ... },
    "inbound": { ... }
  },
  "priority_issues": [
    {
      "category": "recruitment",
      "issue": "求人を出しても応募が全く来ない",
      "priority": 5
    }
  ],
  "dx_solutions": { ... },
  "next_steps": { ... },
  "confidence_score": 0.85,
  "created_at": "2024-01-31T14:05:00",
  "summary": "..."
}
```

詳細は `schema/discussion_schema.json` を参照。

## ディレクトリ構成

```
discussion/
├── pyproject.toml                  # プロジェクト設定
├── requirements.txt                # 依存パッケージ
├── .env.example                    # 環境変数テンプレート
├── README.md                       # このファイル
│
├── schema/
│   ├── __init__.py
│   ├── discussion_schema.json      # JSON スキーマ定義（マスター）
│   └── models.py                   # Pydantic モデル
│
├── src/
│   ├── __init__.py
│   ├── main.py                     # CLI エントリーポイント
│   ├── config.py                   # 設定管理
│   ├── core/                       # 音声・テキスト解析（Phase 2）
│   ├── storage/                    # DB・JSON管理（Phase 3）
│   ├── commands/                   # CLI コマンド実装（Phase 2/3）
│   └── utils/                      # ユーティリティ
│
├── data/
│   ├── audio/                      # 商談音声ファイル
│   ├── records/                    # 抽出された JSON 記録
│   └── db.sqlite                   # SQLite データベース
│
├── tests/                          # テストファイル
└── docs/                           # ドキュメント
```

## 開発ロードマップ

### Phase 1（✅ 完了）
- JSON スキーマ・Pydantic モデル定義
- CLI 基本構造
- プロジェクト設定

### Phase 2（🔄 実装中）
- Whisper 音声認識
- Claude API テキスト解析
- 自動ディスカッション項目抽出
- `process` コマンド実装

### Phase 3（🔄 実装中）
- SQLite データベース設計
- `list-meetings`, `search` コマンド
- `card`, `export` コマンド
- 法人カルテ生成機能

## トラブルシューティング

### API キーエラー
```
Error: ANTHROPIC_API_KEY is not set
```
→ `.env` ファイルで `ANTHROPIC_API_KEY` を設定してください。

### 音声ファイルが見つからない
```
Error: Audio file not found
```
→ ファイルパスが正しいか確認してください。

## テスト

```bash
# すべてのテストを実行
pytest

# カバレッジレポートを表示
pytest --cov=src

# 特定のテストを実行
pytest tests/test_models.py -v
```

## ドキュメント

- `docs/ARCHITECTURE.md` - システムアーキテクチャ詳細
- `docs/API_USAGE.md` - Claude API の使用方法
- `docs/CLI_REFERENCE.md` - CLI コマンドリファレンス
- `docs/SCHEMA_DEFINITION.md` - スキーマ定義詳細

## ライセンス

MIT License

## お問い合わせ

Tabelog Sales Team - souta55908@gmail.com
