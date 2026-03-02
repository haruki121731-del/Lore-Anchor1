# Make.com Blueprints

## セットアップ手順

### 1. シナリオのインポート

1. [make.com](https://make.com) にログイン
2. Scenarios → **Import Blueprint**
3. 以下のファイルをそれぞれインポート:
   - `scenario-llm-router.json` — GitHub Issue → LLM自動コーディング
   - `scenario-design-pipeline.json` — Figma設計 → コード生成 + Canvaマーケ

### 2. 接続の設定 (既存の接続を再利用)

| 接続 | 用途 | ファイル内の置換箇所 |
|------|------|---------------------|
| OpenAI | タスク分類・コード生成 | `__OPENAI_CONNECTION_ID__` |
| Notion | ログ記録 | `__NOTION_CONNECTION_ID__` |

### 3. 変数の置換

Blueprint JSONを開き、以下を実際の値に置換:

```
__GITHUB_TOKEN__      → your GitHub PAT (Settings → Developer settings → Personal access tokens)
__GITHUB_REPO__       → haruki121731-del/lore-anchor (or your repo)
__COVIBE_ROUTER_URL__ → ngrok URLを実行後に取得
                        $ ngrok http 8888
                        → https://abc123.ngrok.io
__FIGMA_TOKEN__       → Figma Settings → Personal access tokens
__CANVA_TOKEN__       → https://developer.canva.com/
__NOTION_DATABASE_ID__→ NotionのデータベースID
```

### 4. GitHubのWebhook設定

1. GitHubリポジトリ → Settings → Webhooks → Add webhook
2. Payload URL: Make.comの webhook URL (`シナリオ1`のトリガーURLをコピー)
3. Content type: `application/json`
4. Events: Issues のみ

### 5. ローカルRouterの起動 + ngrok公開

```bash
# ターミナル1: Router起動
cd Lore-Anchor-
pip install -r covibe-router/requirements.txt
python3 covibe-router/router.py

# ターミナル2: Make.comからアクセス可能にする
ngrok http 8888
# → URLをコピーして __COVIBE_ROUTER_URL__ に設定
```

## シナリオフロー図

### Scenario 1: LLM Router
```
GitHub Issue (labeled: ai-code)
    ↓ Webhook
[Make.com]
    ↓ OpenAI gpt-4o-mini → classify complexity
    ↓ HTTP POST → covibe-router
         ├── simple  → Ollama qwen2.5-coder:7b (LOCAL FREE)
         ├── medium  → Claude Haiku
         └── complex → Claude Sonnet
    ↓ GitHub API → post code as comment
    ↓ GitHub API → add label (ai-coded-local / ai-coded-claude)
    ↓ Notion → log task, cost, model
```

### Scenario 2: Design Pipeline
```
Webhook (figma_url + component_name + feature_description)
    ↓
[Make.com]
    ↓ Figma API → fetch design screenshot
    ↓ OpenAI Vision (GPT-4o) → generate React component
    ↓ OpenAI (gpt-4o-mini) → generate Japanese marketing copy
    ↓ Canva API → create social card design
    ↓ GitHub API → create issue with code
    ↓ Notion → log design task
```
