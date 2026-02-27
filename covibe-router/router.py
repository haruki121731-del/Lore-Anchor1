#!/usr/bin/env python3
"""
covibe-router/router.py
=======================
Hybrid LLM Task Router — Lore-Anchor Dev System
Routes coding tasks between:
  - Ollama (local, free): simple tasks (boilerplate, tests, small fixes)
  - Groq/Haiku (cheap, fast): medium tasks (feature additions, refactors)
  - Claude Sonnet/Opus (powerful): complex tasks (architecture, security, cross-system)

API:
  POST /classify   { title, body, labels } → { complexity, strategy, model, reason }
  POST /execute    { task_id, title, body, repo, branch } → { status, result, pr_url }
  GET  /health     → { ollama: bool, claude: bool, groq: bool }
  GET  /metrics    → { tasks_routed, tokens_saved, cost_saved_usd }
"""

import os
import json
import time
import subprocess
import asyncio
import logging
from typing import Literal
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(
    title="Lore-Anchor LLM Router",
    description="Routes coding tasks to Ollama (local) or Claude based on complexity",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ─────────────────────────────────────────────────────────────────────
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
COVIBE_PATH = os.getenv("COVIBE_PATH", str(Path.home() / "co-vibe" / "co-vibe.py"))
METRICS_FILE = Path(__file__).parent / "metrics.json"
RULES_FILE = Path(__file__).parent / "complexity_rules.json"

# ── Complexity Rules ────────────────────────────────────────────────────────────
def load_rules() -> dict:
    if RULES_FILE.exists():
        return json.loads(RULES_FILE.read_text())
    return {
        "simple_keywords": [
            "test", "spec", "typo", "rename", "format", "lint", "docstring",
            "comment", "readme", "console.log", "print(", "type hint",
            "add import", "missing import", "boilerplate", "scaffold", "skeleton",
            "fix spelling", "whitespace", "trailing comma", "semicolon",
        ],
        "complex_keywords": [
            "architecture", "security", "vulnerability", "auth", "jwt", "oauth",
            "race condition", "deadlock", "migration", "database schema",
            "api design", "caching strategy", "performance bottleneck",
            "refactor entire", "redesign", "c2pa", "cryptography", "signature",
            "distributed", "concurrency", "webhook security", "cors policy",
        ],
        "file_count_thresholds": { "simple": 2, "medium": 5 },
        "line_count_thresholds": { "simple": 50, "medium": 200 },
    }


# ── Metrics ─────────────────────────────────────────────────────────────────────
def load_metrics() -> dict:
    if METRICS_FILE.exists():
        return json.loads(METRICS_FILE.read_text())
    return {
        "tasks_routed": 0,
        "local_tasks": 0,
        "claude_tasks": 0,
        "tokens_saved_estimate": 0,
        "cost_saved_usd": 0.0,
        "history": [],
    }


def save_metrics(m: dict):
    METRICS_FILE.write_text(json.dumps(m, indent=2))


# ── Request/Response Models ─────────────────────────────────────────────────────
class ClassifyRequest(BaseModel):
    title: str
    body: str = ""
    labels: list[str] = []
    file_count: int = 0
    line_count: int = 0


class ClassifyResponse(BaseModel):
    complexity: Literal["simple", "medium", "complex"]
    strategy: Literal["fast", "auto", "strong"]  # co-vibe strategy flags
    model: str
    reason: str
    local: bool  # True = Ollama, False = Claude


class ExecuteRequest(BaseModel):
    title: str
    body: str
    repo: str  # owner/repo
    branch: str = "main"
    task_id: str = ""
    dry_run: bool = False


class ExecuteResponse(BaseModel):
    task_id: str
    status: Literal["queued", "running", "done", "error"]
    model_used: str
    result: str = ""
    cost_usd: float = 0.0
    duration_sec: float = 0.0


# ── Classifier ──────────────────────────────────────────────────────────────────
def classify_task(req: ClassifyRequest) -> ClassifyResponse:
    rules = load_rules()
    text = (req.title + " " + req.body).lower()
    labels_lower = [l.lower() for l in req.labels]

    # Label-based overrides
    if any(l in labels_lower for l in ["architecture", "security", "complex"]):
        return ClassifyResponse(
            complexity="complex", strategy="strong",
            model="claude-sonnet-4-6", reason="Label forces complex routing",
            local=False,
        )
    if any(l in labels_lower for l in ["quick-fix", "typo", "docs", "simple"]):
        return ClassifyResponse(
            complexity="simple", strategy="fast",
            model=OLLAMA_MODEL, reason="Label forces simple routing",
            local=True,
        )

    # Keyword scoring
    simple_score = sum(1 for kw in rules["simple_keywords"] if kw in text)
    complex_score = sum(1 for kw in rules["complex_keywords"] if kw in text)

    # Size signals
    thresholds = rules["file_count_thresholds"]
    if req.file_count > thresholds["medium"] or req.line_count > rules["line_count_thresholds"]["medium"]:
        complex_score += 2
    elif req.file_count <= thresholds["simple"] and req.line_count <= rules["line_count_thresholds"]["simple"]:
        simple_score += 1

    # Decision
    if complex_score >= 2 or (complex_score > 0 and complex_score >= simple_score):
        return ClassifyResponse(
            complexity="complex", strategy="strong",
            model="claude-sonnet-4-6",
            reason=f"Complex signals: {complex_score} keywords matched",
            local=False,
        )
    elif simple_score >= 2 or (simple_score > 0 and complex_score == 0):
        return ClassifyResponse(
            complexity="simple", strategy="fast",
            model=OLLAMA_MODEL,
            reason=f"Simple signals: {simple_score} keywords, Ollama handles locally",
            local=True,
        )
    else:
        return ClassifyResponse(
            complexity="medium", strategy="auto",
            model="claude-haiku-4-5-20251001",
            reason="Ambiguous complexity, using balanced model",
            local=False,
        )


# ── Ollama Direct Call ──────────────────────────────────────────────────────────
async def call_ollama(prompt: str, model: str = OLLAMA_MODEL) -> str:
    """Call Ollama directly for simple tasks (no co-vibe overhead)."""
    system_prompt = """You are an expert software engineer working on Lore-Anchor, an AI learning protection SaaS.
Stack: Next.js 14 (App Router), FastAPI, Supabase, Redis, SaladCloud GPU workers, TypeScript, Python.
Produce minimal, clean, production-ready code. Return ONLY the code/patch, no explanations."""

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": f"<system>{system_prompt}</system>\n\n{prompt}",
                "stream": False,
                "options": {"temperature": 0.2, "top_p": 0.9},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")


# ── co-vibe Executor ────────────────────────────────────────────────────────────
async def run_covibe(task: ExecuteRequest, strategy: str) -> tuple[str, float]:
    """Run co-vibe with specified strategy. Returns (output, duration_sec)."""
    prompt = f"""Task: {task.title}

Details:
{task.body}

Repository: {task.repo}
Branch: {task.branch}

Please implement the required changes. Create a minimal, focused implementation.
Output the exact file paths and code changes needed."""

    start = time.monotonic()

    if task.dry_run:
        await asyncio.sleep(0.5)
        return f"[DRY RUN] Would execute with strategy={strategy}\nTask: {task.title}", 0.5

    proc = await asyncio.create_subprocess_exec(
        "python3", COVIBE_PATH,
        "--strategy", strategy,
        "--one-shot", prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env={**os.environ, "COVIBE_AUTO_APPROVE": "true"},
    )
    stdout, _ = await proc.communicate()
    duration = time.monotonic() - start
    return stdout.decode(errors="replace"), duration


# ── Routes ──────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    results = {"router": "ok", "ollama": False, "ollama_model": OLLAMA_MODEL}
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            results["ollama"] = OLLAMA_MODEL in " ".join(models)
            results["ollama_available_models"] = models
    except Exception as e:
        results["ollama_error"] = str(e)
    return results


@app.post("/classify", response_model=ClassifyResponse)
def classify(req: ClassifyRequest):
    return classify_task(req)


@app.post("/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest, background_tasks: BackgroundTasks):
    task_id = req.task_id or f"task-{int(time.time())}"
    classification = classify_task(ClassifyRequest(
        title=req.title, body=req.body,
    ))

    log.info(f"[{task_id}] complexity={classification.complexity} model={classification.model}")

    start = time.monotonic()

    try:
        if classification.local:
            # Use Ollama directly (no co-vibe overhead for simple tasks)
            prompt = f"Task: {req.title}\n\nDetails:\n{req.body}"
            result = await call_ollama(prompt, OLLAMA_MODEL)
            model_used = OLLAMA_MODEL
            cost = 0.0  # Free! Local!
        else:
            result, _ = await run_covibe(req, classification.strategy)
            model_used = classification.model
            # Rough cost estimate (input tokens ~= len/4, output ~= 500 tokens)
            input_tokens = len(req.title + req.body) // 4
            cost = (input_tokens / 1_000_000) * 3.0 + (500 / 1_000_000) * 15.0

        duration = time.monotonic() - start

        # Update metrics
        m = load_metrics()
        m["tasks_routed"] += 1
        if classification.local:
            m["local_tasks"] += 1
            m["tokens_saved_estimate"] += (len(req.title + req.body) // 4) + 500
            m["cost_saved_usd"] += 0.015  # ~1.5¢ per task saved
        else:
            m["claude_tasks"] += 1
        m["history"].append({
            "task_id": task_id,
            "model": model_used,
            "complexity": classification.complexity,
            "duration_sec": round(duration, 2),
            "cost_usd": round(cost, 5),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        m["history"] = m["history"][-100:]  # keep last 100
        save_metrics(m)

        return ExecuteResponse(
            task_id=task_id,
            status="done",
            model_used=model_used,
            result=result[:5000],  # cap for API response
            cost_usd=round(cost, 5),
            duration_sec=round(duration, 2),
        )

    except Exception as e:
        log.error(f"[{task_id}] execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
def metrics():
    m = load_metrics()
    return {
        **m,
        "local_percentage": round(
            m["local_tasks"] / max(m["tasks_routed"], 1) * 100, 1
        ),
        "cost_saved_usd": round(m.get("cost_saved_usd", 0), 4),
    }


# ── Canva + Figma extensions ─────────────────────────────────────────────────
try:
    from canva_bridge import canva_router
    app.include_router(canva_router)
    log.info("Canva router mounted at /canva/*")
except ImportError:
    log.warning("canva_bridge not found — Canva endpoints disabled")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888, reload=True)
