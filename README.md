# lore-anchor: Project Master Design Document (MDD)

> **⚠️ FOR AI AGENT (Claude Code/Opus):**
> このドキュメントは `lore-anchor` プロジェクトの唯一の正解情報（Single Source of Truth）です。
> 実装時は常にこのドキュメントの定義に従ってください。変更が必要な場合は、必ずユーザーの許可を得てからこのドキュメントを更新してください。
> **最優先事項:** 「推測」で実装せず、定義されたスタックとアーキテクチャを厳守すること。

---

## 1. プロジェクト概要 (Project Context)

### 1.1 ビジョン
**lore-anchor** は、画像生成AIによる無断学習からクリエイターを保護し、権利を証明し、収益化へ繋げる次世代の著作権管理インフラです。

### 1.2 コアバリュー (MVP Scope)
1.  **Shield (防御):** ユーザーが画像をアップロードすると、自動的に「Mist v2」（AI学習阻害ノイズ）が適用される。
2.  **Trust (証明):** 画像には「PixelSeal」（不可視透かし）と「C2PA」（来歴証明署名）が埋め込まれる。
3.  **Speed (体験):** これら高度な処理を、安価な分散型GPUクラウド（SaladCloud）を用いて低遅延・低コストで提供する。

---

## 2. システムアーキテクチャ (Architecture)

### 2.1 ハイレベル構成図
```mermaid
graph LR
    User[👤 Creator] -- HTTPS/Drag&Drop --> FE[Frontend (Next.js)]
    FE -- POST /upload --> API[Backend API (FastAPI)]
    API -- Auth & Metadata --> DB[(Supabase PG)]
    API -- Push Task --> Queue[Redis Queue]
    
    subgraph "Worker Cluster (SaladCloud)"
        Worker[🚀 GPU Worker (Python)] -- Pull Task --> Queue
        Worker -- 1.Download --> R2_Temp[R2 Storage (Temp)]
        Worker -- 2.Watermark --> PixelSeal[💎 PixelSeal Lib]
        Worker -- 3.Protection --> Mist[🛡️ Mist v2 Lib]
        Worker -- 4.Sign --> C2PA[🔏 C2PA Tool]
        Worker -- 5.Upload --> R2_Final[R2 Storage (Public)]
    end
    
    Worker -- Webhook/Status Update --> API
    API -- SSE/Polling --> FE

```

### 2.2 技術スタック (Tech Stack) - **Strict Constraint**

これ以外の技術選定は原則禁止とする。

| Layer | Technology | Version / Note |
| --- | --- | --- |
| **Frontend** | **Next.js** | App Router, TypeScript, Tailwind CSS, shadcn/ui |
| **Backend** | **FastAPI** | Python 3.10+, Pydantic v2, AsyncIO |
| **Database** | **Supabase** | PostgreSQL, Auth (Email/Google), Storage (Wrapper) |
| **Queue** | **Redis** | Upstash (Serverless) or Self-hosted on Railway |
| **Storage** | **Cloudflare R2** | AWS S3 Compatible API (boto3) |
| **GPU Worker** | **Python (Docker)** | Base: `nvidia/cuda:12.1.0-runtime-ubuntu22.04` |
| **Core Libs** | **PyTorch** | CUDA 12.1 support |
| **Defense** | **Mist v2** | *Custom Implementation* (See Section 4) |
| **Watermark** | **Meta Seal (PixelSeal)** | *Custom Implementation* (See Section 4) |

---

## 3. ディレクトリ構造 (Directory Structure)

Monorepo構成を採用する。

```text
lore-anchor/
├── .github/              # CI/CD workflows
├── apps/
│   ├── web/              # Frontend (Next.js)
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/          # Supabase Client, API wrappers
│   └── api/              # Backend (FastAPI)
│       ├── main.py
│       ├── routers/
│       ├── models/       # Pydantic Schemas
│       └── services/     # Redis/DB Logic
├── workers/
│   └── gpu-worker/       # Python GPU Worker
│       ├── Dockerfile    # The most critical file
│       ├── main.py       # Worker entrypoint (Celery/Arq)
│       ├── core/
│       │   ├── mist/     # Mist v2 logic
│       │   └── seal/     # PixelSeal logic
│       └── requirements.txt
├── packages/             # Shared logic (types, configs)
├── docker-compose.yml    # For local development
└── README.md             # This file

```

---

## 4. クリティカル・ロジック詳細 (Core Logic specs)

**注意:** 画像処理パイプラインの順序は**絶対不可逆**である。逆順にすると保護が無効化されるか、透かしが破壊される。

### 4.1 GPU Worker Pipeline (The "Defense" Logic)

1. **Input:** 原本画像 (`original_image`) をR2からダウンロード。
2. **Step 1: Watermarking (PixelSeal)**
* `original_image` に対して不可視透かし（128bit ID）を埋め込む。
* Output: `watermarked_image`
* *Reason:* Mistのノイズ適用前に埋め込まないと、Mist自体が透かしを「敵対的ノイズ」とみなして破壊する可能性があるため。また、Mist適用後の画像改変（Resize等）に透かしが耐える必要がある。


3. **Step 2: Adversarial Attack (Mist v2)**
* `watermarked_image` に対してMist v2処理を実行。
* Parameters: `epsilon=8` (Standard), `steps=3` (Speed priority).
* Output: `protected_image`


4. **Step 3: C2PA Signing**
* `protected_image` のメタデータに署名を付与。
* Assertions: `"c2pa.training-mining": "not-allowed"`


5. **Output:** `protected_image` をR2の公開バケットへアップロードし、URLを返却。

### 4.2 データベース設計 (Supabase)

```sql
-- Users Table (Managed by Supabase Auth)
-- public.profiles linked to auth.users

create table public.images (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users not null,
  original_url text not null, -- R2 Private URL
  protected_url text,         -- R2 Public URL (Initially null)
  watermark_id text,          -- Generated UUID for PixelSeal
  status text default 'pending', -- pending, processing, completed, failed
  c2pa_manifest jsonb,
  created_at timestamptz default now()
);

create table public.tasks (
  id uuid default gen_random_uuid() primary key,
  image_id uuid references public.images not null,
  worker_id text,
  started_at timestamptz,
  completed_at timestamptz,
  error_log text
);

```

---

## 5. 実装ロードマップ & チェックリスト (Implementation Steps)

AIエージェントは以下の順序で実装を進めること。各フェーズ完了時に必ず動作確認を行うこと。

### ✅ Phase 1: Infrastructure & Worker (The Hardest Part)

GPU処理が動かなければこのプロダクトは成立しないため、ここから着手する。

* [ ] **GPU Worker実装:**
* `workers/gpu-worker/` を作成。
* Mist v2 と PixelSeal のコードを含める（GitHub等のOSSからクローンまたは移植）。
* `main.py` で画像を受け取り、Step1〜3を実行するスクリプトを作成。


* [ ] **Docker化:**
* `nvidia/cuda` ベースのDockerfileを作成。
* PyTorch等の依存関係を解決し、ビルドが通ることを確認。


* [ ] **Local Testing:**
* ローカルGPU（またはColab環境）でコンテナを起動し、画像1枚を処理して出力結果を確認。



### ✅ Phase 2: Backend API & Queue

* [ ] **FastAPI Setup:**
* `apps/api` をセットアップ。
* `/upload` エンドポイント実装（Supabase Auth検証込み）。
* R2へのPre-signed URL発行、またはサーバー経由アップロード実装。


* [ ] **Queue Connection:**
* APIからRedisへタスクをPushする処理。
* GPU WorkerからRedisをPoll（またはSubscribe）する処理の統合。



### ✅ Phase 3: Frontend (UX)

* [ ] **Next.js Setup:**
* `apps/web` をセットアップ。
* Supabase Auth UIの実装。


* [ ] **Upload UI:**
* Drag & Drop ゾーンの実装。
* アップロード進捗バー。
* SSE (Server-Sent Events) または ポーリングによる処理状況のリアルタイム表示。


* [ ] **Dashboard:**
* `protected_url` が生成されたら画像を表示し、ダウンロード可能にする。



---

## 6. 環境変数 (Environment Variables)

`.env` ファイルに必要な変数は以下の通り。

```ini
# Supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Cloudflare R2
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=

# Redis
REDIS_URL=

# Worker Config
MIST_EPSILON=8
MIST_STEPS=3

```

---

## 7. AI Agentへの指示 (Prompt Instructions)

**Claude Code / Opus へ:**

1. **小さな単位で実行せよ:** 一気に全ファイルを作成しようとせず、「まずWorkerのDockerfileを作る」「次にAPIの定義を書く」というようにステップバイステップで進めてください。
2. **エラーハンドリング:** 画像処理はGPUメモリ不足などで失敗する可能性が高いです。必ず `try-except` で捕捉し、DBの `status` を `failed` に更新するロジックを入れてください。
3. **コンテキスト維持:** `apps/web` を触っているときに `workers/` のロジックを勝手に変更しないでください。境界を意識してください。
4. **コード品質:** 型ヒント（Type Hints）を必ず記述し、可読性を維持してください。

**Start Command:**
まず `workers/gpu-worker` のディレクトリを作成し、Mist v2とPixelSealを動かすための `requirements.txt` と `Dockerfile` のドラフトを作成してください。
