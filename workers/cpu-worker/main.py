"""
Lore-Anchor CPU Worker

Free tier processing worker that runs on CPU only.
- PixelSeal (DWT-based, no ML)
- Mist v2 freq mode (DCT-based, no ML model download)

This worker is designed to run on Railway alongside the API,
providing free tier processing without GPU costs.
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import boto3
import requests
from PIL import Image

# Import core processing modules
from core.mist.mist_v2 import apply_mist_v2, MistMode
from core.seal.pixelseal import embed_watermark

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Environment variables
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "lore-anchor")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api-production-550c.up.railway.app")

# Processing config
PROCESSING_TIMEOUT = 120  # seconds


def get_r2_client() -> boto3.client:
    """Create R2/S3 compatible client."""
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def update_task_status(
    image_id: str,
    status: str,
    protected_url: str | None = None,
    error_log: str | None = None,
) -> bool:
    """Update task status via Supabase API."""
    try:
        headers = {
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        
        # Update images table
        data: dict[str, Any] = {"status": status}
        if protected_url:
            data["protected_url"] = protected_url
        
        resp = requests.patch(
            f"{SUPABASE_URL}/rest/v1/images?id=eq.{image_id}",
            headers=headers,
            json=data,
            timeout=30,
        )
        resp.raise_for_status()
        
        # Update tasks table
        task_data: dict[str, Any] = {
            "completed_at": datetime.utcnow().isoformat(),
        }
        if error_log:
            task_data["error_log"] = error_log
        
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/tasks?image_id=eq.{image_id}",
            headers=headers,
            json=task_data,
            timeout=30,
        )
        
        return True
    except Exception as exc:
        logger.error(f"Failed to update task status: {exc}")
        return False


def download_image(r2_client: boto3.client, original_url: str) -> Image.Image:
    """Download image from R2."""
    # Extract key from URL
    if "/" in original_url:
        key = original_url.split("/")[-1].split("?")[0]
    else:
        key = original_url
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        r2_client.download_file(R2_BUCKET_NAME, key, tmp.name)
        img = Image.open(tmp.name).convert("RGB")
        os.unlink(tmp.name)
        return img


def upload_image(
    r2_client: boto3.client,
    image: Image.Image,
    image_id: str,
) -> str:
    """Upload processed image to R2 and return public URL."""
    key = f"protected/{image_id}.png"
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        image.save(tmp.name, "PNG")
        r2_client.upload_file(
            tmp.name,
            R2_BUCKET_NAME,
            key,
            ExtraArgs={"ContentType": "image/png"},
        )
        os.unlink(tmp.name)
    
    # Build public URL
    public_domain = os.getenv("R2_PUBLIC_DOMAIN", "")
    if public_domain:
        return f"https://{public_domain}/{key}"
    return f"{R2_ENDPOINT_URL}/{R2_BUCKET_NAME}/{key}"


def process_image_cpu(
    image: Image.Image,
    watermark_id: str,
    epsilon: int = 8,
    steps: int = 3,
) -> Image.Image:
    """
    Process image using CPU-only methods.
    
    Pipeline:
    1. PixelSeal watermark (DWT-based, CPU only)
    2. Mist v2 freq mode (DCT-based, CPU only)
    """
    logger.info(f"Starting CPU processing with watermark_id={watermark_id}")
    
    # Step 1: PixelSeal watermark
    logger.info("Applying PixelSeal watermark...")
    watermarked = embed_watermark(image, watermark_id, backend="dwt")
    
    # Step 2: Mist v2 freq mode (CPU-friendly)
    logger.info("Applying Mist v2 freq mode...")
    protected = apply_mist_v2(
        watermarked,
        epsilon=epsilon,
        steps=steps,
        mode=MistMode.FREQ,  # CPU mode
        device=None,
    )
    
    logger.info("CPU processing complete")
    return protected


def process_task(task_data: dict[str, Any]) -> bool:
    """Process a single task from the queue."""
    image_id = task_data.get("image_id")
    original_url = task_data.get("original_url")
    watermark_id = task_data.get("watermark_id")
    
    if not all([image_id, original_url, watermark_id]):
        logger.error(f"Invalid task data: {task_data}")
        return False
    
    logger.info(f"Processing task: image_id={image_id}")
    
    # Update status to processing
    update_task_status(image_id, "processing")
    
    r2_client = get_r2_client()
    
    try:
        # Download original image
        logger.info(f"Downloading image from {original_url}")
        image = download_image(r2_client, original_url)
        
        # Process with CPU-only methods
        processed = process_image_cpu(
            image,
            watermark_id,
            epsilon=8,
            steps=3,
        )
        
        # Upload processed image
        logger.info("Uploading processed image...")
        protected_url = upload_image(r2_client, processed, image_id)
        
        # Update status to completed
        update_task_status(image_id, "completed", protected_url)
        logger.info(f"Task completed: {image_id}")
        return True
        
    except Exception as exc:
        logger.error(f"Processing failed: {exc}", exc_info=True)
        update_task_status(image_id, "failed", error_log=str(exc)[:500])
        return False


def get_pending_tasks() -> list[dict[str, Any]]:
    """Fetch pending tasks from Supabase (free tier only)."""
    try:
        headers = {
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        }
        
        # Get pending tasks for free tier users
        # For now, process all pending (we'll filter by tier in the API later)
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/images?status=eq.pending&order=created_at.asc&limit=5",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        
        tasks = []
        for image in resp.json():
            tasks.append({
                "image_id": image["id"],
                "original_url": image["original_url"],
                "watermark_id": image.get("watermark_id") or str(uuid.uuid4()).replace("-", ""),
            })
        
        return tasks
    except Exception as exc:
        logger.error(f"Failed to fetch pending tasks: {exc}")
        return []


def main_loop():
    """Main worker loop."""
    logger.info("=" * 50)
    logger.info("Lore-Anchor CPU Worker Starting...")
    logger.info("=" * 50)
    logger.info(f"API_BASE_URL: {API_BASE_URL}")
    logger.info(f"SUPABASE_URL configured: {'Yes' if SUPABASE_URL else 'No'}")
    logger.info(f"R2_ENDPOINT configured: {'Yes' if R2_ENDPOINT_URL else 'No'}")
    
    # Validate config
    if not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, R2_ENDPOINT_URL]):
        logger.error("Missing required environment variables!")
        logger.error("Please set: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, R2_ENDPOINT_URL")
        sys.exit(1)
    
    while True:
        try:
            # Fetch pending tasks
            tasks = get_pending_tasks()
            
            if not tasks:
                logger.debug("No pending tasks, sleeping...")
                time.sleep(5)
                continue
            
            logger.info(f"Found {len(tasks)} pending tasks")
            
            # Process each task
            for task in tasks:
                success = process_task(task)
                if not success:
                    logger.warning(f"Task failed: {task.get('image_id')}")
                
                # Small delay between tasks
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as exc:
            logger.error(f"Main loop error: {exc}", exc_info=True)
            time.sleep(10)


def run_single_task(image_id: str):
    """Run a single task for testing."""
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/images?id=eq.{image_id}",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    
    images = resp.json()
    if not images:
        logger.error(f"Image not found: {image_id}")
        return
    
    image = images[0]
    task = {
        "image_id": image["id"],
        "original_url": image["original_url"],
        "watermark_id": image.get("watermark_id") or str(uuid.uuid4()).replace("-", ""),
    }
    
    success = process_task(task)
    logger.info(f"Task result: {'success' if success else 'failed'}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Lore-Anchor CPU Worker")
    parser.add_argument("--single", help="Process single image by ID")
    args = parser.parse_args()
    
    if args.single:
        run_single_task(args.single)
    else:
        main_loop()
