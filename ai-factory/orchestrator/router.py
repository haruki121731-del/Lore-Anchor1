#!/usr/bin/env python3
"""
AI Development Factory - Task Router
ローカルLLM並列実行のためのタスクルーティングエンジン

co-vibeとの統合により、複数のOllamaインスタンスに負荷分散
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path

import yaml
import redis.asyncio as redis
from aiohttp import web, ClientSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class ModelConfig:
    name: str
    context_length: int
    temperature: float
    vram_required_gb: int
    avg_tokens_per_sec: int
    quality_score: int


@dataclass
class Worker:
    id: str
    host: str
    port: int
    gpu: str
    vram_gb: int
    max_concurrent: int
    models: List[str]
    priority: str
    current_load: int = 0
    healthy: bool = True
    last_health_check: float = 0
    
    @property
    def ollama_url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    @property
    def vram_available(self) -> int:
        # 簡易的な計算（実際は動的に取得）
        used_vram = sum(
            6 if "7b" in m else 12 if "14b" in m or "13b" in m else 22
            for m in self.models[:self.current_load]
        )
        return self.vram_gb - used_vram


@dataclass
class Task:
    id: str
    description: str
    prompt: str
    task_type: str
    difficulty: str
    model_tier: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    assigned_worker: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 2


class LLMRouter:
    """
    タスクを最適なローカルLLMワーカーにルーティング
    """
    
    def __init__(self, config_path: str = "config/llm-cluster.yaml"):
        self.config = self.load_config(config_path)
        self.workers: Dict[str, Worker] = {}
        self.models: Dict[str, ModelConfig] = {}
        self.redis_client: Optional[redis.Redis] = None
        self.session: Optional[ClientSession] = None
        self.running = False
        
        self.initialize()
    
    def load_config(self, path: str) -> dict:
        """設定ファイルを読み込み"""
        with open(path) as f:
            return yaml.safe_load(f)
    
    def initialize(self):
        """初期化"""
        # ワーカー設定
        for tier_name, tier_workers in self.config["workers"].items():
            for w_config in tier_workers:
                worker = Worker(
                    id=w_config["id"],
                    host=w_config["host"],
                    port=w_config["port"],
                    gpu=w_config["gpu"],
                    vram_gb=w_config["vram_gb"],
                    max_concurrent=w_config["max_concurrent"],
                    models=w_config["models"],
                    priority=w_config["priority"]
                )
                self.workers[worker.id] = worker
        
        # モデル設定
        for tier_name, tier_models in self.config["models"].items():
            for model_name, model_config in tier_models.items():
                self.models[model_name] = ModelConfig(
                    name=model_name,
                    **model_config
                )
        
        logger.info(f"Initialized {len(self.workers)} workers, {len(self.models)} models")
    
    async def start(self):
        """サービス開始"""
        self.running = True
        self.session = ClientSession()
        
        # Redis接続
        redis_config = self.config["cluster"]["queue"]
        self.redis_client = redis.Redis(
            host=redis_config["host"],
            port=redis_config["port"],
            db=redis_config["db"],
            decode_responses=True
        )
        
        # ヘルスチェック開始
        asyncio.create_task(self.health_check_loop())
        
        # タスク処理開始
        asyncio.create_task(self.task_processor_loop())
        
        logger.info("Router started")
    
    async def stop(self):
        """サービス停止"""
        self.running = False
        if self.session:
            await self.session.close()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Router stopped")
    
    async def health_check_loop(self):
        """定期的なヘルスチェック"""
        interval = self.config["routing"]["load_balancing"]["health_check_interval"]
        
        while self.running:
            for worker in self.workers.values():
                try:
                    async with self.session.get(
                        f"{worker.ollama_url}/api/tags",
                        timeout=5
                    ) as resp:
                        worker.healthy = resp.status == 200
                        worker.last_health_check = time.time()
                        
                        if worker.healthy:
                            # 現在の負荷を取得
                            data = await resp.json()
                            worker.current_load = len(data.get("models", []))
                            
                except Exception as e:
                    logger.warning(f"Health check failed for {worker.id}: {e}")
                    worker.healthy = False
            
            await asyncio.sleep(interval)
    
    async def task_processor_loop(self):
        """タスク処理メインループ"""
        while self.running:
            try:
                # Redisキューからタスクを取得
                task_data = await self.redis_client.blpop("task_queue", timeout=1)
                
                if task_data:
                    _, task_json = task_data
                    task = self.deserialize_task(task_json)
                    
                    # タスク実行
                    asyncio.create_task(self.process_task(task))
                    
            except Exception as e:
                logger.error(f"Task processor error: {e}")
                await asyncio.sleep(1)
    
    async def process_task(self, task: Task):
        """タスクを処理"""
        try:
            # ワーカー選択
            worker = self.select_optimal_worker(task)
            
            if not worker:
                raise Exception("No available worker")
            
            task.assigned_worker = worker.id
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            
            # モデル選択
            model = self.select_model_for_task(task)
            
            # Ollama API呼び出し
            result = await self.call_ollama(worker, model, task)
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            
            # 結果をRedisに保存
            await self.redis_client.setex(
                f"result:{task.id}",
                3600,  # 1時間保持
                json.dumps({
                    "status": "completed",
                    "result": result,
                    "worker": worker.id,
                    "model": model,
                    "duration": task.completed_at - task.started_at
                })
            )
            
            logger.info(f"Task {task.id} completed by {worker.id}")
            
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            task.error = str(e)
            task.retry_count += 1
            
            if task.retry_count <= task.max_retries:
                task.status = TaskStatus.RETRYING
                # 再キューイング
                await self.redis_client.rpush(
                    "task_queue",
                    self.serialize_task(task)
                )
            else:
                task.status = TaskStatus.FAILED
                await self.redis_client.setex(
                    f"result:{task.id}",
                    3600,
                    json.dumps({
                        "status": "failed",
                        "error": str(e),
                        "retries": task.retry_count
                    })
                )
    
    def select_optimal_worker(self, task: Task) -> Optional[Worker]:
        """
        タスクに最適なワーカーを選択
        アダプティブ負荷分散
        """
        # タスク要件に基づくフィルタリング
        required_vram = self.get_required_vram(task)
        suitable_models = self.get_suitable_models(task)
        
        candidates = []
        for worker in self.workers.values():
            # ヘルスチェック
            if not worker.healthy:
                continue
            
            # VRAMチェック
            if worker.vram_available < required_vram:
                continue
            
            # モデル対応チェック
            has_model = any(m in worker.models for m in suitable_models)
            if not has_model:
                continue
            
            # キュー容量チェック
            if worker.current_load >= worker.max_concurrent:
                continue
            
            # スコア計算
            score = self.calculate_worker_score(worker, task)
            candidates.append((worker, score))
        
        if not candidates:
            return None
        
        # 最高スコアのワーカーを選択
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    def calculate_worker_score(self, worker: Worker, task: Task) -> float:
        """
        ワーカーの適合スコアを計算
        """
        score = 0.0
        
        # 1. VRAM availability (0-30)
        vram_ratio = worker.vram_available / worker.vram_gb
        score += vram_ratio * 30
        
        # 2. Model availability (0-25)
        if task.model_tier == "fast":
            target_models = ["qwen2.5-coder:7b", "codellama:7b", "phi4"]
        elif task.model_tier == "balanced":
            target_models = ["qwen2.5-coder:14b", "codellama:13b", "deepseek-coder:16b"]
        else:
            target_models = ["qwen2.5-coder:32b", "codellama:34b", "deepseek-coder:33b"]
        
        has_target = any(any(t in m for t in target_models) for m in worker.models)
        if has_target:
            score += 25
        
        # 3. Load factor (0-25)
        load_ratio = 1 - (worker.current_load / worker.max_concurrent)
        score += load_ratio * 25
        
        # 4. Priority match (0-10)
        priority_map = {
            TaskPriority.CRITICAL: 10,
            TaskPriority.HIGH: 7,
            TaskPriority.NORMAL: 5,
            TaskPriority.LOW: 3
        }
        
        if worker.priority == "high":
            score += priority_map.get(task.priority, 5)
        elif worker.priority == "normal":
            score += priority_map.get(task.priority, 5) * 0.7
        else:
            score += priority_map.get(task.priority, 5) * 0.4
        
        # 5. Recent health (0-10)
        time_since_check = time.time() - worker.last_health_check
        if time_since_check < 60:
            score += 10
        elif time_since_check < 300:
            score += 5
        
        return score
    
    def select_model_for_task(self, task: Task) -> str:
        """
        タスクに適したモデルを選択
        """
        tier_models = {
            "fast": ["qwen2.5-coder:7b-q4_K_M", "codellama:7b-code-q4"],
            "balanced": ["qwen2.5-coder:14b-q5", "deepseek-coder:16b-q5"],
            "powerful": ["qwen2.5-coder:32b-q4", "deepseek-coder:33b-q4"],
            "expert": ["qwq:32b-preview-q4"]
        }
        
        candidates = tier_models.get(task.model_tier, tier_models["balanced"])
        
        # ワーカーが対応している最初のモデルを選択
        worker = self.workers.get(task.assigned_worker)
        if worker:
            for model in candidates:
                if model in worker.models:
                    return model
        
        return candidates[0]
    
    async def call_ollama(
        self,
        worker: Worker,
        model: str,
        task: Task
    ) -> str:
        """
        Ollama APIを呼び出し
        """
        model_config = self.models.get(model, {})
        
        payload = {
            "model": model,
            "prompt": task.prompt,
            "stream": False,
            "options": {
                "temperature": model_config.temperature if model_config else 0.7,
                "num_ctx": model_config.context_length if model_config else 32768,
                "num_predict": 4096
            }
        }
        
        async with self.session.post(
            f"{worker.ollama_url}/api/generate",
            json=payload,
            timeout=120
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Ollama error: {resp.status}")
            
            data = await resp.json()
            return data.get("response", "")
    
    def get_required_vram(self, task: Task) -> int:
        """
        タスクに必要なVRAMを推定
        """
        vram_map = {
            "fast": 6,
            "balanced": 12,
            "powerful": 22,
            "expert": 24
        }
        return vram_map.get(task.model_tier, 12)
    
    def get_suitable_models(self, task: Task) -> List[str]:
        """
        タスクに適したモデル一覧を取得
        """
        tier_map = {
            "fast": ["qwen2.5-coder:7b", "codellama:7b", "phi4"],
            "balanced": ["qwen2.5-coder:14b", "codellama:13b", "deepseek-coder:16b"],
            "powerful": ["qwen2.5-coder:32b", "codellama:34b", "deepseek-coder:33b"],
            "expert": ["qwq", "mixtral:8x22b"]
        }
        return tier_map.get(task.model_tier, tier_map["balanced"])
    
    def classify_task(self, description: str) -> tuple:
        """
        タスクを分類
        """
        patterns = self.config["routing"]["classification"]["patterns"]
        desc_lower = description.lower()
        
        for task_type, config in patterns.items():
            keywords = config.get("keywords", [])
            if any(kw.lower() in desc_lower for kw in keywords):
                return (
                    task_type,
                    config["difficulty"],
                    config["model_tier"]
                )
        
        return ("general", "medium", "balanced")
    
    def serialize_task(self, task: Task) -> str:
        """タスクをJSONにシリアライズ"""
        return json.dumps({
            "id": task.id,
            "description": task.description,
            "prompt": task.prompt,
            "task_type": task.task_type,
            "difficulty": task.difficulty,
            "model_tier": task.model_tier,
            "priority": task.priority.value,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries
        })
    
    def deserialize_task(self, json_str: str) -> Task:
        """JSONからタスクをデシリアライズ"""
        data = json.loads(json_str)
        return Task(
            id=data["id"],
            description=data["description"],
            prompt=data["prompt"],
            task_type=data["task_type"],
            difficulty=data["difficulty"],
            model_tier=data["model_tier"],
            priority=TaskPriority(data.get("priority", 3)),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 2)
        )
    
    async def submit_task(
        self,
        description: str,
        prompt: str,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """
        新しいタスクを提出
        """
        task_id = f"task_{int(time.time() * 1000)}"
        
        # タスク分類
        task_type, difficulty, model_tier = self.classify_task(description)
        
        task = Task(
            id=task_id,
            description=description,
            prompt=prompt,
            task_type=task_type,
            difficulty=difficulty,
            model_tier=model_tier,
            priority=priority
        )
        
        # キューに追加
        await self.redis_client.rpush(
            "task_queue",
            self.serialize_task(task)
        )
        
        logger.info(f"Task {task_id} submitted")
        return task_id
    
    async def get_result(self, task_id: str, timeout: int = 60) -> Optional[dict]:
        """
        タスク結果を取得
        """
        start = time.time()
        
        while time.time() - start < timeout:
            result = await self.redis_client.get(f"result:{task_id}")
            if result:
                return json.loads(result)
            
            await asyncio.sleep(0.5)
        
        return None


# HTTP APIエンドポイント
async def submit_handler(request: web.Request):
    """タスク提出エンドポイント"""
    router = request.app["router"]
    
    data = await request.json()
    description = data.get("description", "")
    prompt = data.get("prompt", "")
    priority_val = data.get("priority", 3)
    priority = TaskPriority(priority_val)
    
    task_id = await router.submit_task(description, prompt, priority)
    
    return web.json_response({
        "task_id": task_id,
        "status": "queued"
    })


async def result_handler(request: web.Request):
    """結果取得エンドポイント"""
    router = request.app["router"]
    task_id = request.match_info["task_id"]
    
    result = await router.get_result(task_id, timeout=5)
    
    if result:
        return web.json_response(result)
    else:
        return web.json_response(
            {"status": "pending"},
            status=202
        )


async def status_handler(request: web.Request):
    """ステータス確認エンドポイント"""
    router = request.app["router"]
    
    workers_status = {
        wid: {
            "healthy": w.healthy,
            "load": w.current_load,
            "vram_available": w.vram_available,
            "models": w.models
        }
        for wid, w in router.workers.items()
    }
    
    return web.json_response({
        "workers": workers_status,
        "queue_length": await router.redis_client.llen("task_queue")
    })


async def main():
    """メインエントリポイント"""
    router = LLMRouter()
    await router.start()
    
    app = web.Application()
    app["router"] = router
    
    app.router.add_post("/api/v1/submit", submit_handler)
    app.router.add_get("/api/v1/result/{task_id}", result_handler)
    app.router.add_get("/api/v1/status", status_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "localhost", 8090)
    await site.start()
    
    logger.info("API server started on http://localhost:8090")
    
    # 永続実行
    while router.running:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
