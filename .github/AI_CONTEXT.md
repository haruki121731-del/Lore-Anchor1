# 🤖 AI Work Context — Lore-Anchor

> **Auto-updated by AI agents. Any AI can pick up work from this file.**
> Last updated: see git log

## Current System Status

| Component | Status | Notes |
|-----------|--------|-------|
| co-vibe router | ✅ built | `covibe-router/router.py` — FastAPI on port 8888 |
| Ollama integration | ✅ configured | `qwen2.5-coder:7b` for simple tasks |
| GitHub Actions | ✅ built | `.github/workflows/ai-code.yml` |
| Make.com scenarios | ⏳ pending | blueprints in `.make/` directory |
| Figma integration | ⏳ pending | script in `covibe-router/figma_bridge.py` |
| Canva integration | ⏳ pending | script in `covibe-router/canva_bridge.py` |
| Marketing automation | ✅ built | `haruki121731-del/marketing` repo |

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

- [ ] Install Ollama locally: `bash setup-covibe.sh`
- [ ] Start router: `pip install -r covibe-router/requirements.txt && python3 covibe-router/router.py`
- [ ] Import Make.com blueprints from `.make/` directory
- [ ] Connect Figma → Make.com webhook (see `.make/scenario-design-pipeline.json`)
- [ ] Add GitHub secrets: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GROQ_API_KEY`
- [ ] Label any GitHub issue `ai-code` to trigger auto-coding

## How to Use (Quick Start)

```bash
# 1. One-time setup
bash setup-covibe.sh

# 2. Start the LLM router locally
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
