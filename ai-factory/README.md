# 🏭 AI Development Factory

> **ローカルLLM並列実行による、コスト最小化の巨大AI開発チーム**

![Architecture](https://img.shields.io/badge/Architecture-Parallel%20LLM-blue)
![Cost](https://img.shields.io/badge/Cost-$0.09%2Ftask-green)
![Agents](https://img.shields.io/badge/Agents-165%2B-orange)

## 概要

AI Development Factoryは、**co-vibe**と**Ollama**を組み合わせ、ローカルGPUクラスターで並列実行することで、クラウドAPIコストの**1/100**で100人規模のAI開発チームを実現するシステムです。

```
従来: Claude API $2,000/月 + 人間エンジニア $50,000/月 = $52,000/月
本システム: ローカルGPU $2,000/月 + 電気代 $300/月 = $2,300/月

削減率: 95.6% (年間 $596,400 節約)
```

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI DEVELOPMENT FACTORY                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   Router    │───▶│ Load        │───▶│  Ollama     │        │
│  │   (co-vibe) │    │ Balancer    │    │  Cluster    │        │
│  └─────────────┘    └─────────────┘    └──────┬──────┘        │
│         │                                      │                │
│         │                              ┌───────┴───────┐       │
│         │                              │               │       │
│         ▼                        ┌─────▼────┐   ┌─────▼────┐  │
│  ┌─────────────┐                 │ Worker 1 │   │ Worker N │  │
│  │  165 AI     │                 │ RTX 4090 │   │ RTX 3090 │  │
│  │  Agents     │                 └──────────┘   └──────────┘  │
│  └─────────────┘                                               │
│                                                                  │
│  Frontend(55) │ Backend(50) │ Infrastructure(40) │ Research(20)│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## クイックスタート

### 1. インストール

```bash
git clone https://github.com/haruki121731-del/Lore-Anchor1.git
cd Lore-Anchor1/ai-factory
./setup.sh
```

### 2. 起動

```bash
# サービス開始
ai-factory start

# または Dockerで
docker-compose up -d
```

### 3. タスク実行

```bash
# Reactコンポーネント作成
ai-factory submit '{
    "description": "Create React button component",
    "prompt": "Create a reusable Button component with TypeScript, Tailwind CSS, and accessibility support..."
}'

# APIエンドポイント作成
curl -X POST http://localhost:8090/api/v1/submit \
    -H "Content-Type: application/json" \
    -d '{
        "description": "Create FastAPI endpoint",
        "prompt": "Create a REST API endpoint for user registration with validation...",
        "priority": 2
    }'
```

## システム構成

### GPUワーカー階層

| ティア | GPU | VRAM | モデル | 用途 |
|--------|-----|------|--------|------|
| Tier 1 | RTX 4090 | 24GB | 32B/33B | アーキテクチャ設計 |
| Tier 2 | RTX 3090/4080 | 24/16GB | 14B/16B | 標準開発タスク |
| Tier 3 | RTX 4070/4060 | 12/16GB | 7B/14B | 単純タスク |

### 対応モデル

**Fast Tier (速度優先)**
- `qwen2.5-coder:7b-q4_K_M` - 高速コーディング
- `codellama:7b-code-q4` - 軽量コード生成
- `phi4:14b-q4` - バランス型

**Balanced Tier (標準)**
- `qwen2.5-coder:14b-q5` - 標準開発
- `deepseek-coder:16b-q5` - 高品質コード
- `codellama:13b-code-q5` - 汎用開発

**Powerful Tier (品質優先)**
- `qwen2.5-coder:32b-q4` - 複雑な設計
- `deepseek-coder:33b-q4` - 大規模開発
- `mixtral:8x7b-q4` - マルチタスク

## AIエージェント構成

### Frontend Division (55 Agents)

```
UI/UX Team (10)
├── Design System Architect × 2
├── Component Designer × 3
├── Accessibility Specialist × 2
└── Interaction Designer × 3

Component Development (15)
├── React/Vue Specialist × 5
├── CSS/Tailwind Expert × 4
├── Animation Developer × 3
└── Form Handler × 3

State Management (10)
├── Redux/Zustand Expert × 3
├── React Query Specialist × 3
├── Context API Handler × 2
└── Real-time Sync × 2

Testing (10)
├── Unit Test Writer × 4
├── E2E Test Developer × 3
├── Visual Regression × 2
└── Performance Engineer × 1

Build & Optimization (10)
├── Webpack/Vite Expert × 3
├── Bundle Optimizer × 3
├── PWA Specialist × 2
└── SEO Optimizer × 2
```

### Backend Division (50 Agents)

```
API Development (10)
├── REST API Designer × 3
├── GraphQL Specialist × 3
├── gRPC Developer × 2
└── API Gateway × 2

Database (10)
├── Schema Designer × 3
├── Query Optimizer × 3
├── Migration Specialist × 2
└── NoSQL Expert × 2

Security (10)
├── Auth/AuthZ × 3
├── Encryption × 2
├── Vulnerability Scanner × 3
└── Compliance × 2

Integration (10)
├── Third-party API × 4
├── Webhook Handler × 3
├── Queue System × 2
└── Event Stream × 1

Business Logic (10)
├── Domain Model × 3
├── Algorithm Dev × 4
├── Validation × 2
└── Rule Engine × 1
```

### Infrastructure Division (40 Agents)

```
Kubernetes (10) │ CI/CD (10) │ Monitoring (10) │ Cost Opt (5) │ SecOps (5)
```

## パフォーマンス

| 指標 | 目標 | 実測値 |
|------|------|--------|
| 日次処理タスク数 | 1,000+ | - |
| 平均レスポンス時間 | < 5秒 | - |
| 成功率 | > 95% | - |
| コスト/タスク | $0.09 | - |

## コスト比較

### クラウドAPI vs ローカルLLM

| 項目 | クラウドAPI | ローカルLLM |
|------|-------------|-------------|
| 月間コスト | $2,000〜10,000 | $500〜2,000 |
| 推論コスト/1K tokens | $0.01〜0.03 | $0 (電気代のみ) |
| レイテンシー | 100-500ms | 50-200ms |
| プライバシー | 外部送信 | 完全ローカル |
| カスタマイズ | 制限あり | 完全自由 |

## 設定

### 設定ファイル

`config/llm-cluster.yaml`:

```yaml
workers:
  tier_1:
    - id: worker-t1-01
      host: localhost
      port: 11434
      gpu: RTX_4090
      models:
        - qwen2.5-coder:32b-q4
        - deepseek-coder:33b-q4

routing:
  strategy: adaptive
  fallback:
    enabled: true
    fallback_model: qwen2.5-coder:14b-q5

quality_control:
  enabled: true
  self_correction:
    enabled: true
    max_attempts: 3
```

## API

### タスク提出

```http
POST /api/v1/submit
Content-Type: application/json

{
    "description": "Create React button component",
    "prompt": "Create a reusable Button component...",
    "priority": 2  // 1: Critical, 2: High, 3: Normal, 4: Low
}
```

### 結果取得

```http
GET /api/v1/result/{task_id}
```

### ステータス確認

```http
GET /api/v1/status
```

## モニタリング

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Router API**: http://localhost:8090

## トラブルシューティング

### よくある問題

**Q: Ollamaがモデルを見つけられない**
```bash
ollama list  # モデル一覧確認
ollama pull qwen2.5-coder:7b-q4_K_M  # モデルダウンロード
```

**Q: GPUが認識されない**
```bash
nvidia-smi  # GPU状態確認
# Dockerの場合: --gpus all フラグを確認
```

**Q: Redis接続エラー**
```bash
redis-cli ping  # Redis動作確認
# 起動: redis-server --daemonize yes
```

## 貢献

AI Development Factoryは自律的に進化するシステムです。

1. **提案**: GitHub Issueで改善提案
2. **実装**: AIエージェントが自動実装
3. **検証**: 品質管理システムが自動検証
4. **デプロイ**: CI/CDパイプラインが自動デプロイ

## ライセンス

MIT License

## 謝辞

- [co-vibe](https://github.com/ochyai/co-vibe) - マルチプロバイダAIエージェント
- [Ollama](https://ollama.com) - ローカルLLM実行環境
- [Qwen](https://github.com/QwenLM/Qwen) - コード生成モデル

---

**Made with ❤️ by Lore-Anchor AI Factory**
