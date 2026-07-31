# Next.js + HeroUI フロントエンドセットアップ

このガイドでは、Next.js と HeroUI を使った Web UI を構築します。

## セットアップ手順

### 1. Next.js プロジェクトを作成

```bash
# discussion フォルダの外で実行
cd ..
npx create-next-app@latest discussion-web --typescript --tailwind

# 質問に答える（デフォルトでOK）
# - TypeScript: Yes
# - ESLint: Yes
# - Tailwind CSS: Yes
# - App Router: Yes

cd discussion-web
```

### 2. HeroUI をインストール

```bash
npm install @heroui/react @heroui/theme framer-motion
npm install -D tailwindcss@latest postcss autoprefixer
```

### 3. tailwind.config.ts を設定

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss'
const { heroui } = require("@heroui/react");

const config: Config = {
  content: [
    './node_modules/@heroui/react/dist/**/*.{js,ts,jsx,tsx}',
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  darkMode: "class",
  plugins: [heroui()],
}
export default config
```

### 4. 環境変数を設定

```bash
# .env.local を作成
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
```

### 5. フロントエンドコンポーネントを作成

**app/layout.tsx:**
```typescript
import type { Metadata } from 'next'
import { Providers } from './providers'
import './globals.css'

export const metadata: Metadata = {
  title: 'Discussion System - 商談解析',
  description: '食べログ営業向け商談音声解析システム',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}
```

**app/providers.tsx:**
```typescript
'use client'

import { HeroUIProvider } from "@heroui/react"

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <HeroUIProvider>
      {children}
    </HeroUIProvider>
  )
}
```

**app/page.tsx:**
```typescript
'use client'

import { useState } from 'react'
import { Card, CardBody, CardHeader, Divider, Button, Input, Select, SelectItem, Progress, Chip } from "@heroui/react"
import { Upload, Search, BookOpen } from 'lucide-react'

export default function Home() {
  const [activeTab, setActiveTab] = useState<'process' | 'list' | 'search' | 'card'>('process')

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* ヘッダー */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">商談解析システム</h1>
          <p className="text-gray-600">食べログ営業向け音声自動解析</p>
        </div>

        {/* タブナビゲーション */}
        <div className="flex gap-3 mb-8">
          <Button
            className={`px-6 py-2 rounded-lg font-semibold transition ${
              activeTab === 'process'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300'
            }`}
            startContent={<Upload size={18} />}
            onClick={() => setActiveTab('process')}
          >
            音声処理
          </Button>
          <Button
            className={`px-6 py-2 rounded-lg font-semibold transition ${
              activeTab === 'list'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300'
            }`}
            onClick={() => setActiveTab('list')}
          >
            一覧
          </Button>
          <Button
            className={`px-6 py-2 rounded-lg font-semibold transition ${
              activeTab === 'search'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300'
            }`}
            startContent={<Search size={18} />}
            onClick={() => setActiveTab('search')}
          >
            検索
          </Button>
          <Button
            className={`px-6 py-2 rounded-lg font-semibold transition ${
              activeTab === 'card'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300'
            }`}
            startContent={<BookOpen size={18} />}
            onClick={() => setActiveTab('card')}
          >
            法人カルテ
          </Button>
        </div>

        {/* コンテンツエリア */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* メインコンテンツ */}
          <div className="lg:col-span-2">
            {activeTab === 'process' && <ProcessTab />}
            {activeTab === 'list' && <ListTab />}
            {activeTab === 'search' && <SearchTab />}
            {activeTab === 'card' && <CardTab />}
          </div>

          {/* サイドバー */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-bold mb-4">📊 最新情報</h3>
            <div className="space-y-3">
              <div className="text-sm text-gray-600">
                <p className="font-semibold text-gray-900">商談件数</p>
                <p className="text-2xl font-bold text-blue-600">12</p>
              </div>
              <Divider />
              <div className="text-sm text-gray-600">
                <p className="font-semibold text-gray-900">企業数</p>
                <p className="text-2xl font-bold text-green-600">5</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// タブコンポーネント
function ProcessTab() {
  const [file, setFile] = useState<File | null>(null)
  const [company, setCompany] = useState('')
  const [contact, setContact] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState(0)

  const handleProcess = async () => {
    if (!file || !company) return

    setIsLoading(true)
    setProgress(0)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('company_name', company)
      formData.append('contact_name', contact)

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/process`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) throw new Error('処理失敗')

      const data = await response.json()
      setProgress(100)
      alert('✓ 処理完了！信頼度: ' + Math.round(data.confidence_score * 100) + '%')
    } catch (error) {
      alert('✗ エラーが発生しました')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className="w-full">
      <CardHeader className="flex gap-3">
        <Upload className="w-5 h-5" />
        <div className="flex flex-col">
          <p className="text-lg font-semibold">音声ファイルを処理</p>
          <p className="text-sm text-gray-500">商談音声を自動解析します</p>
        </div>
      </CardHeader>
      <Divider />
      <CardBody className="gap-4">
        <div className="border-2 border-dashed border-blue-300 rounded-lg p-8 text-center cursor-pointer hover:bg-blue-50 transition">
          <input
            type="file"
            accept=".mp3,.wav,.m4a,.flac,.ogg"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="hidden"
            id="audio-input"
          />
          <label htmlFor="audio-input" className="cursor-pointer">
            <p className="text-gray-600 font-semibold">
              {file ? file.name : 'ファイルをドラッグ & ドロップ'}
            </p>
            <p className="text-sm text-gray-500 mt-2">または選択してアップロード</p>
          </label>
        </div>

        <Input
          label="店舗名"
          placeholder="レストランA"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          isRequired
        />

        <Input
          label="接触者氏名"
          placeholder="山田太郎"
          value={contact}
          onChange={(e) => setContact(e.target.value)}
        />

        {isLoading && <Progress value={progress} className="max-w-md" />}

        <Button
          onClick={handleProcess}
          isDisabled={!file || !company || isLoading}
          className="bg-blue-600 text-white font-semibold py-3 rounded-lg hover:bg-blue-700"
        >
          {isLoading ? '処理中...' : '処理を開始'}
        </Button>
      </CardBody>
    </Card>
  )
}

function ListTab() {
  return (
    <Card>
      <CardHeader>商談一覧</CardHeader>
      <CardBody>
        <p className="text-gray-600">実装中...</p>
      </CardBody>
    </Card>
  )
}

function SearchTab() {
  return (
    <Card>
      <CardHeader>課題検索</CardHeader>
      <CardBody>
        <p className="text-gray-600">実装中...</p>
      </CardBody>
    </Card>
  )
}

function CardTab() {
  return (
    <Card>
      <CardHeader>法人カルテ</CardHeader>
      <CardBody>
        <p className="text-gray-600">実装中...</p>
      </CardBody>
    </Card>
  )
}
```

## 起動方法

### ターミナル1: Python FastAPI バックエンド

```bash
cd discussion  # Python プロジェクトディレクトリ
source venv/bin/activate
python -m uvicorn src.api.main:app --reload --port 8000
```

API は **http://localhost:8000** で起動
Swagger UI: **http://localhost:8000/docs**

### ターミナル2: Next.js フロントエンド

```bash
cd discussion-web  # Next.js プロジェクトディレクトリ
npm run dev
```

フロントエンドは **http://localhost:3000** で起動

---

## セキュリティ機能

✅ **API キーはサーバー側に隠す** - クライアントから見えない
✅ **CORS 対応** - localhost:3000 のみ許可
✅ **ファイル検証** - アップロードサイズ・形式チェック
✅ **入力値バリデーション** - Pydantic で自動チェック
✅ **環境変数管理** - .env で秘密情報を管理

---

## 次のステップ

1. ✅ ProcessTab を完成
2. 🔄 ListTab・SearchTab・CardTab を実装
3. 🔄 データベース連携テスト
4. 🔄 エラーハンドリング
5. 🔄 本番デプロイ（Vercel + Fly.io）

