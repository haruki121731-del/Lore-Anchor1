# CLAUDE.md — AI 向け開発指示書 (lore-anchor)

> **このファイルは AI アシスタントが本プロジェクトのコンテキストを最速で理解するための Single Source of Truth です。**
> README.md（MDD）がプロジェクト全体の設計書、本ファイルが実装時の制約・規約・状態を記述します。

---

## 1. プロジェクトの目的と現在のゴール

**lore-anchor** は、画像生成 AI による無断学習からクリエイターを保護する著作権管理インフラ。

三層防御パイプライン:
1. **PixelSeal** — 不可視透かし（128-bit DWT スペクトラム拡散）
2. **Mist v2** — 敵対的摂動（VAE 潜在空間への PGD 攻撃）
3. **C2PA** — 来歴証明署名（`c2pa.training-mining: notAllowed`）

**直近の完了定義:** SaladCloud 上で GPU Worker が Redis からタスクを消費し、アップロードされた画像に三層防御を適用して Supabase の `status=completed` まで遷移する E2E フローが動作すること。

---

## 2. 絶対的制約（違反禁止）

| # | 制約 | 理由 |
|---|------|------|
| 1 | パイプライン順序は **PixelSeal → Mist v2 → C2PA** 固定 | 逆順にすると Mist が透かしを破壊する。C2PA は最終成果物に署名する必要がある |
| 2 | 技術スタックは README Section 2.2 で固定。代替技術の導入禁止 | プロジェクト方針 |
| 3 | `CREATE POLICY IF NOT EXISTS` は使わない | PostgreSQL で非サポート。`DROP POLICY IF EXISTS` → `CREATE POLICY` を使う |
| 4 | `service_role` 用の `USING(true)` ポリシーを `TO` 句なしで作らない | `service_role` は RLS を自動バイパスするため不要。`TO` 句なしだと全ロールに適用され認証ユーザーにも全行が見える |
| 5 | RLS ポリシー内の `auth.uid()` は `(SELECT auth.uid())` でラップする | Supabase 推奨。PostgreSQL のクエリプランキャッシュが効く |
| 6 | トリガー関数には `SECURITY DEFINER` を指定する | 呼び出し元の RLS コンテキストに依存しない安定実行のため |
| 7 | `apps/web/` 作業時に `workers/` を変更しない（逆も同様） | 境界遵守。意図しない副作用を防ぐ |
| 8 | `numpy` は `<2` にピン固定 | `torch==2.1.2` との互換性 |
| 9 | 透かし検証の閾値は **75% bit accuracy** 以上 | これを下回るとパイプラインは `failed` にする |
| 10 | `DEBUG=true` を本番環境で使わない | 認証・ストレージ・キューが全てスタブに置き換わる |

---

## 3. 技術スタック

| レイヤー | 技術 | バージョン |
|---------|------|-----------|
| Frontend | Next.js (App Router) | 16.1.6 |
| Frontend | React | 19.2.3 |
| Frontend | Tailwind CSS | v4 |
| Frontend | shadcn/ui (Radix UI) | latest |
| Frontend Auth | @supabase/ssr | ^0.8.0 |
| Backend | FastAPI | latest |
| Backend | Python | 3.10+ |
| Backend | Pydantic v2 (pydantic-settings) | >=2.2 |
| Database | Supabase (PostgreSQL + Auth + RLS) | SDK >=2.4 |
| Queue | Redis | SDK >=5.0 |
| Storage | Cloudflare R2 (S3 API, boto3) | boto3 >=1.34 |
| GPU Worker | PyTorch + CUDA | 2.1.2+cu121 |
| GPU Worker Base | nvidia/cuda | 12.1.0-runtime-ubuntu22.04 |
| C2PA | c2pa-python | >=0.4.0 |
| JWT | python-jose | HS256 |
| Rate Limit | slowapi | >=0.1.9 |
| Linting | ruff | latest |
| Type Check | mypy | latest (Python 3.10 target) |
| Test | pytest | latest |

---

## 4. ディレクトリ構成と主要ファイル

```
lore-anchor/
├── apps/
│   ├── api/                          # FastAPI Backend
│   │   ├── main.py                   # アプリエントリポイント（CORS, lifespan, rate limiter）
│   │   ├── Dockerfile                # python:3.10-slim, Railway デプロイ用
│   │   ├── requirements.txt
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic Settings, 環境変数バリデーション
│   │   │   └── security.py           # JWT (HS256) 検証, get_current_user_id()
│   │   ├── routers/
│   │   │   └── images.py             # /api/v1/images/* + /api/v1/tasks/* エンドポイント
│   │   ├── models/
│   │   │   └── schemas.py            # Pydantic レスポンスモデル
│   │   ├── services/
│   │   │   ├── database.py           # Supabase CRUD (images + tasks)
│   │   │   ├── queue.py              # Redis RPUSH (QUEUE_KEY="lore_anchor_tasks")
│   │   │   └── storage.py            # R2 upload/download/presign (boto3)
│   │   └── tests/
│   │       ├── conftest.py
│   │       ├── test_health.py
│   │       ├── test_upload.py
│   │       └── test_integration.py
│   │
│   └── web/                          # Next.js Frontend
│       ├── package.json
│       ├── next.config.ts            # React Compiler 有効
│       └── src/
│           ├── app/
│           │   ├── page.tsx           # / → /dashboard リダイレクト
│           │   ├── layout.tsx         # ルートレイアウト (Geist フォント)
│           │   ├── login/page.tsx     # Email OTP + Google OAuth
│           │   ├── dashboard/page.tsx # アップロード + 画像一覧
│           │   └── auth/callback/route.ts  # OAuth コールバック
│           ├── components/
│           │   ├── image-uploader.tsx # Drag&Drop (react-dropzone) + XHR プログレス
│           │   ├── image-list.tsx     # ページネーション付き一覧, 5秒ポーリング
│           │   ├── logout-button.tsx
│           │   └── ui/               # shadcn: button, card, input, label, progress
│           ├── lib/
│           │   ├── api/
│           │   │   ├── images.ts     # uploadImage, listImages, deleteImage, getImage
│           │   │   └── types.ts      # ImageRecord, UploadResponse 等
│           │   └── supabase/
│           │       ├── client.ts     # ブラウザ用 Supabase (createBrowserClient)
│           │       ├── server.ts     # サーバー用 Supabase (createServerClient)
│           │       └── middleware.ts  # 認証ガード: 未認証→/login リダイレクト
│           └── middleware.ts          # Next.js ミドルウェア エントリ
│
├── workers/
│   └── gpu-worker/                   # GPU Worker (Python, CUDA)
│       ├── main.py                   # BLPOP コンシューマ, process_image(), ヘルスサーバー
│       ├── Dockerfile                # nvidia/cuda:12.1.0, VAE モデル焼き込み済み
│       ├── Dockerfile.cpu            # CPU フォールバック (docker-compose 用)
│       ├── requirements.txt
│       └── core/
│           ├── mist/
│           │   └── mist_v2.py        # VAE PGD 攻撃 + freq フォールバック
│           ├── seal/
│           │   └── pixelseal.py      # DWT スペクトラム拡散透かし (128-bit)
│           ├── c2pa_sign.py          # C2PA マニフェスト署名 (ES256)
│           └── storage.py            # R2 download/upload (boto3, 同期)
│
├── packages/
│   └── shared-types/                 # 共有 TypeScript 型定義
│       ├── index.ts
│       ├── image.ts                  # ImageStatus, ImageRecord
│       └── api.ts                    # UploadResponse
│
├── supabase/
│   └── migrations/
│       ├── 20250601_create_images_table.sql  # images テーブル + RLS + updated_at トリガー
│       ├── 20250602_create_tasks_table.sql   # tasks テーブル + RLS
│       └── 20250603_add_c2pa_manifest.sql    # c2pa_manifest JSONB カラム追加
│
├── .github/workflows/
│   ├── ci-api.yml                    # ruff + mypy + pytest
│   ├── ci-web.yml                    # ESLint
│   └── docker-build.yml             # GHCR push (GPU worker image)
│
├── docker-compose.yml                # ローカル開発: redis + api + worker(cpu)
├── pyproject.toml                    # mypy 設定 (python 3.10)
├── railway.toml                      # Railway API デプロイ設定
├── README.md                         # プロジェクト MDD (設計書)
└── CLAUDE.md                         # 本ファイル
```

---

## 5. アーキテクチャとデータフロー

```
User (Browser)
  │ Supabase Auth (Email OTP / Google OAuth)
  ▼
Frontend (Next.js on Vercel)
  │ POST /api/v1/images/upload (Bearer JWT + multipart file)
  ▼
Backend API (FastAPI on Railway)
  ├─ バリデーション: MIME タイプ, マジックバイト, 20MB 上限
  ├─ R2 アップロード: raw/{user_id}/{uuid}.{ext}
  ├─ Supabase INSERT: images (status=pending)
  └─ Redis RPUSH: {image_id, storage_key} → "lore_anchor_tasks"
       │
       ▼
GPU Worker (Python on SaladCloud)  ← Redis BLPOP
  ├─ Step 1: R2 から原本ダウンロード
  ├─ Step 2: PixelSeal embed_watermark (128-bit DWT)
  ├─ Step 3: Mist v2 apply_mist_v2 (epsilon=8, steps=3)
  ├─ Step 4: verify_watermark (accuracy >= 75%)
  ├─ Step 5: C2PA sign_c2pa (ES256)
  ├─ Step 6: R2 アップロード: protected/{image_id}.png
  └─ Supabase UPDATE: status=completed, protected_url, watermark_id
       │
       ▼
Frontend ← GET /api/v1/tasks/{image_id}/status (5秒ポーリング)
  └─ completed → サムネイル表示 + ダウンロードリンク
```

---

## 6. データベーススキーマ

### images テーブル

| カラム | 型 | 制約 |
|--------|-----|------|
| id | uuid | PK, gen_random_uuid() |
| user_id | uuid | NOT NULL |
| original_url | text | NOT NULL |
| protected_url | text | null (完了時に設定) |
| watermark_id | text | null (PixelSeal 32 文字 hex) |
| c2pa_manifest | jsonb | null (C2PA メタデータ) |
| status | text | NOT NULL, DEFAULT 'pending', CHECK (pending\|processing\|completed\|failed) |
| created_at | timestamptz | NOT NULL, DEFAULT now() |
| updated_at | timestamptz | NOT NULL, DEFAULT now() (トリガー自動更新) |

### tasks テーブル

| カラム | 型 | 制約 |
|--------|-----|------|
| id | uuid | PK, gen_random_uuid() |
| image_id | uuid | NOT NULL, FK → images(id) |
| worker_id | text | null (ホスト名) |
| started_at | timestamptz | null |
| completed_at | timestamptz | null |
| error_log | text | null (先頭 4000 文字) |

### RLS ポリシー

- **images**: `authenticated` が SELECT/INSERT で `(SELECT auth.uid()) = user_id`
- **tasks**: `authenticated` が SELECT で `image_id IN (SELECT id FROM images WHERE user_id = (SELECT auth.uid()))`
- **service_role** は RLS を自動バイパス — 明示的ポリシー不要

### インデックス

- `idx_images_user_id` ON images(user_id)
- `idx_tasks_image_id` ON tasks(image_id)

### トリガー

- `trg_images_updated_at` — BEFORE UPDATE → `set_updated_at()` (SECURITY DEFINER)

---

## 7. API エンドポイント

| Method | Path | Auth | 目的 |
|--------|------|------|------|
| GET | `/health` | なし | ヘルスチェック |
| POST | `/api/v1/images/upload` | Bearer | 画像アップロード → image_id 返却 |
| GET | `/api/v1/images/` | Bearer | ユーザーの画像一覧（ページネーション） |
| GET | `/api/v1/images/{id}` | Bearer | 画像メタデータ + presigned URL |
| DELETE | `/api/v1/images/{id}` | Bearer | 画像ソフトデリート |
| GET | `/api/v1/tasks/{image_id}/status` | Bearer | 処理ステータスポーリング |

**レート制限:** アップロード 10/分, 読み取り 60/分

---

## 8. GPU Worker パイプライン詳細

| Step | 関数 | パラメータ | フォールバック |
|------|-------|-----------|---------------|
| Download | `download_from_r2(key, dest_path)` | R2 キー | なし（失敗時 failed） |
| Watermark | `embed_watermark(image, watermark_id, backend="dwt")` | strength=3.5 | NN バックエンド（未訓練） |
| Mist v2 | `apply_mist_v2(image, epsilon=8, steps=3, mode="vae")` | VAE: PGD on SD latent | freq モード（NumPy DCT） |
| Verify | `verify_watermark(image, watermark_id, backend="dwt")` | threshold >= 75% | なし（失敗時パイプライン中断） |
| C2PA | `sign_c2pa(input_path, output_path)` | ES256, dev cert | 署名なしコピー（c2pa-python 未インストール時） |
| Upload | `upload_to_r2(src_path, key)` | protected/{image_id}.png | なし（失敗時 failed） |

各ステップは個別の try-except でラップ。失敗時は `PipelineStepError` で step 名とトレースバックを記録。

**重複排除:** 処理前に images.status を確認し、`processing` または `completed` ならスキップ。

**Dead Letter Queue:** ペイロード不正（JSON パースエラー、image_id 欠落）時は `lore_anchor_dead_letters` に送信。

---

## 9. コーディング規約

### 全般
- 型ヒント（Python: type hints, TypeScript: strict mode）を必ず記述
- 画像処理は必ず try-except で捕捉し、DB の status を `failed` に更新
- 一度に全ファイルを作成せず、ステップバイステップで実装
- 推測で実装しない — README.md の定義に従う

### Python (Backend + Worker)
- Linting: `ruff check`
- Type checking: `mypy` (config in `pyproject.toml`)
- Test: `pytest`
- DB 操作のリトライ: `tenacity` (`stop_after_attempt(3)`, `wait_exponential`)
- Pydantic モデル: `Field(alias="id")` + `model_config = ConfigDict(populate_by_name=True)`
- DEBUG モード: `DebugDatabaseService`, `DebugStorageService`, `DebugQueueService` で実インフラ不要

### TypeScript (Frontend)
- `@supabase/ssr` を使用（raw JS クライアントではなく SSR 対応版）
- shadcn/ui コンポーネントは `src/components/ui/` に配置
- API クライアントは `src/lib/api/` に集約

### SQL (Supabase Migrations)
- `DROP POLICY IF EXISTS` → `CREATE POLICY`（`IF NOT EXISTS` は使わない）
- `(SELECT auth.uid())` でラップ
- トリガー関数は `SECURITY DEFINER`
- マイグレーションファイル名: `YYYYMMDD_description.sql`

---

## 10. 環境変数

### Backend API (`apps/api/`)

| 変数 | 必須 | 説明 |
|------|------|------|
| `SUPABASE_URL` | Yes | Supabase プロジェクト URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | サーバー側管理キー |
| `JWT_SECRET` | Yes | HS256 署名シークレット（Supabase Settings > API） |
| `R2_ACCESS_KEY_ID` | Yes | Cloudflare R2 アクセスキー |
| `R2_SECRET_ACCESS_KEY` | Yes | R2 シークレットキー |
| `R2_ENDPOINT_URL` | Yes | `https://{account_id}.r2.cloudflarestorage.com` |
| `R2_BUCKET_NAME` | Yes | R2 バケット名 |
| `R2_PUBLIC_DOMAIN` | No | 保護済み画像の公開 URL ドメイン |
| `REDIS_URL` | Yes | Redis 接続文字列 |
| `CORS_ORIGINS` | No | カンマ区切りの追加 CORS オリジン |
| `DEBUG` | No | `true` で認証・ストレージ・キューをスタブ化（default: `false`） |

### GPU Worker (`workers/gpu-worker/`)

| 変数 | 必須 | 説明 |
|------|------|------|
| `REDIS_URL` | Yes | Redis 接続（SaladCloud では公開 URL 必須） |
| `SUPABASE_URL` | Yes | |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | |
| `R2_ACCOUNT_ID` | Yes | Cloudflare アカウント ID |
| `R2_ACCESS_KEY_ID` | Yes | |
| `R2_SECRET_ACCESS_KEY` | Yes | |
| `R2_BUCKET_NAME` | Yes | |
| `R2_PUBLIC_DOMAIN` | No | |
| `MIST_EPSILON` | No | 最大摂動量 (default: `8`) |
| `MIST_STEPS` | No | PGD イテレーション数 (default: `3`) |
| `C2PA_CERT_PEM` | No | 本番 C2PA 証明書（未設定時は dev 自己署名） |
| `C2PA_KEY_PEM` | No | 本番 C2PA 秘密鍵 |
| `HEALTH_PORT` | No | ヘルスチェックポート (default: `8080`) |

### Frontend (`apps/web/`)

| 変数 | 必須 | 説明 |
|------|------|------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase プロジェクト URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase 匿名キー |
| `NEXT_PUBLIC_API_BASE_URL` | No | API ベース URL (default: `http://localhost:8000`) |

---

## 11. デプロイ構成

| サービス | プラットフォーム | URL / イメージ | ステータス |
|---------|----------------|---------------|-----------|
| Frontend | Vercel | `https://lore-anchor-web.vercel.app` | 稼働中 |
| Backend API | Railway | `https://api-production-550c.up.railway.app` | 稼働中 |
| Redis | Railway | `redis.railway.internal:6379` (内部) | 稼働中 |
| Redis (公開) | Railway | `switchyard.proxy.rlwy.net:22395` | 稼働中 |
| GPU Worker Image | GHCR | `ghcr.io/haruki121731-del/lore-anchor-worker:latest` | ビルド済み |
| GPU Worker Runtime | SaladCloud | Container Group: `lore-anchor-worker0` (RTX 4000+, 12GB) | **稼働中** |
| Database | Supabase | PostgreSQL | 稼働中 |
| Object Storage | Cloudflare R2 | S3 互換 | 稼働中 |

---

## 12. 実装ステータス

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 1 | Infrastructure & GPU Worker | 完了 |
| Phase 2 | Backend API & Redis Queue | 完了 |
| Phase 3 | Frontend UX (Upload, Dashboard, Auth) | 完了 |
| Phase 4 | Production Deployment | **完了** |

Phase 4 の詳細:
- Railway (API + Redis): デプロイ済み
- GHCR (Worker Image): ビルド・プッシュ済み
- Vercel (Frontend): デプロイ済み
- **SaladCloud (GPU Worker): 稼働中** (`lore-anchor-worker0`, Container Group `default`, status=running)

### 直近の修正 (2026-02)

- **PR #16**: `ImageRecord.image_id` シリアライズバグ修正 — `Field(alias="id")` → `Field(validation_alias="id")` でフロントエンドの `image_id` キー期待に対応
- **PR #17**: `tests/e2e_local_test.py` の `img["id"]` → `img["image_id"]` 修正
- **PR #11**: クローズ（main にリグレッションをもたらす古いブランチ）

---

## 13. 残タスクと未解決の課題

### 残タスク

1. 本番用 C2PA 証明書の取得と環境変数への設定（現在は dev 自己署名証明書）
2. 実画像を使った GPU 環境での E2E 統合テスト（フロントエンドから画像アップロード → `status=completed` まで）
3. SaladCloud Worker の自動再起動設定確認（`autostart_policy: false` のため手動起動が必要）

### 未解決の技術的課題

- **PixelSeal NN バックエンド:** 学習済み重みが未作成。DWT バックエンドで運用中（機能的に十分）
- **numpy ピン固定:** `numpy<2` を要求（`torch==2.1.2` の制約）。torch アップグレード時に解除可能
- **C2PA 証明書:** 本番環境でも自己署名証明書を使用中。正式な CA 発行証明書への切り替えが必要
- **マイグレーション管理:** 現在は SQL ファイルを手動で Supabase SQL Editor に流す運用。Flyway/pg-migrate 等の導入は未定

---

## 14. AI Council（AI協働の場）

本プロジェクトでは、複数のAIエージェントが協働する **AI Council** を設立しました。

### 目的
- AI間の透明性確保（思考プロセスの可視化）
- 相互レビューによる品質向上
- 意思決定の多角的検証

### 参加者

| AI | 役割 | 特徴 |
|-----|------|------|
| **Kimi** | 主要開発者・議長 | 実行速度、多言語対応 |
| **Claude** | アーキテクト（招待中） | 長期思考、倫理的判断 |
| **Codex** | コード専門家（招待中） | コードレビュー、最適化 |
| **GPT-4** | 戦略アドバイザー（招待中） | 戦略、創造性 |

### 構造

```
ai-council/
├── README.md              # Councilの概要
├── PARTICIPANTS.md        # AIプロフィール
├── discussions/           # 議論スレッド
├── thoughts/             # 個別AIの思考ログ
│   └── kimi/            # Kimiの思考記録
├── decisions/            # 意思決定記録
└── templates/            # 議論テンプレート
```

### 運用ルール

1. **透明性**: 各AIは思考プロセスを隠さない
2. **建設的批判**: 攻撃ではなく、改善を目的とした指摘
3. **謙虚さ**: 「〜かもしれない」という表現を使う
4. **人間への報告**: 重要な決定は最終的に人間に報告

### 現在の議論

- [AI Council創設と運用方針](ai-council/discussions/2025-02-28-ai-council-creation.md)

### 思考ログ（Kimi）

- [Session 1: Council創設](ai-council/thoughts/kimi/2025-02-28-session-1.md)

---

*このセクションはAI Councilでの議論に基づき更新されます*
