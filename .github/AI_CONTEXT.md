# 🤖 AI Work Context — Lore-Anchor

> **Auto-updated by AI agents. Any AI can pick up work from this file.**
> Last updated: see git log

## Current System Status

| Component | Status | Notes |
|-----------|--------|-------|
| co-vibe router | ✅ RUNNING | `covibe-router/router.py` — port 8888, tested 2026-02-27 |
| Ollama integration | ✅ RUNNING | `qwen2.5-coder:7b` — pulled, tested, LOCAL free routing |
| GitHub Actions | ✅ built | `.github/workflows/ai-code.yml` — label 'ai-code' to trigger |
| Make.com scenarios | ⏳ pending | blueprints in `.make/` — import manually (free plan limit) |
| Figma integration | ⏳ pending | `covibe-router/figma_bridge.py` |
| Canva integration | ⏳ pending | `covibe-router/canva_bridge.py` |
| Marketing automation | ✅ pushed | `haruki121731-del/marketing` — 5 scripts + note article |

## Architecture Decisions (for AI handoff)

### LLM Routing Logic
- **Simple tasks** (tests, typos, boilerplate) → **Ollama `qwen2.5-coder:7b`** (FREE, local)
- **Medium tasks** (features, refactors) → **Claude Haiku** (cheap)
- **Complex tasks** (architecture, security, C2PA) → **Claude Sonnet** (powerful)
- Classifier at: `POST http://localhost:8888/classify`

### Key Files
```
covibe-router/
├── router.py         ← FastAPI classification + execution API
├── complexity_rules.json  ← keyword-based routing rules
└── requirements.txt

setup-covibe.sh        ← one-command setup (Ollama + co-vibe)
.github/workflows/
├── ai-code.yml        ← auto-code issues labeled 'ai-code'
└── save-context.yml   ← auto-save AI work context
.make/
├── scenario-llm-router.json     ← Make.com import blueprint
└── scenario-design-pipeline.json
```

### Product Context (Lore-Anchor)
- **What it is**: AI learning protection SaaS for Japanese illustrators
- **Stack**: Next.js 14 / FastAPI / Supabase / Redis / SaladCloud GPU
- **3-layer protection**: Mist v2 → PixelSeal watermark → C2PA signature
- **Target**: JP creators worried about AI training on their art
- **Differentiator**: "防衛+証明" vs Glaze/Nightshade's "防衛only"
- **Waitlist**: https://waitinglist-xi-sandy.vercel.app

## Pending Tasks (pick up from here)

- [x] Install Ollama locally — done, binary at `/tmp/OllamaApp/Ollama.app/Contents/Resources/ollama`
- [x] Pull qwen2.5-coder:7b — done, models in `~/.ollama/models`
- [x] Start router — done, tested via curl
- [ ] **Persist Ollama across reboots** — on reboot: `bash start-covibe.sh` (re-extracts from Ollama-darwin.zip if needed)
- [ ] Import Make.com blueprints from `.make/` directory (free plan: 2 scenarios max)
- [ ] Connect Figma → Make.com webhook (see `.make/scenario-design-pipeline.json`)
- [ ] Add GitHub secrets: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GROQ_API_KEY`
- [ ] Label any GitHub issue `ai-code` to trigger auto-coding
- [ ] Set up Twitter/Supabase secrets in `haruki121731-del/marketing` repo for auto-posting

## How to Use (Quick Start)

```bash
# 1. Start everything (after reboot)
bash start-covibe.sh

# 2. Or manually:
# Start the LLM router locally
python3 covibe-router/router.py &

# 3. Classify a task
curl -X POST http://localhost:8888/classify \
  -H 'Content-Type: application/json' \
  -d '{"title": "Add unit tests for C2PA signing", "body": ""}'
# → {"complexity": "simple", "model": "qwen2.5-coder:7b", "local": true}

# 4. Execute with auto-routing
curl -X POST http://localhost:8888/execute \
  -H 'Content-Type: application/json' \
  -d '{"title": "Add unit tests for C2PA signing", "body": "Write pytest tests for apps/api/c2pa.py", "repo": "harukiuesaka/lore-anchor"}'

# 5. Check cost savings
curl http://localhost:8888/metrics | jq
```

## For AI Agents Taking Over

If you are an AI agent continuing this work:

1. Read this file first
2. Check `git log --oneline -20` to see recent changes
3. Run `curl http://localhost:8888/health` to verify local services
4. Issues labeled `ai-context` contain detailed task logs
5. Make.com blueprints are in `.make/` — import these if scenarios are missing
6. The marketing repo is at `github.com/haruki121731-del/marketing`

## Context History

<!-- Auto-appended by .github/workflows/save-context.yml -->
