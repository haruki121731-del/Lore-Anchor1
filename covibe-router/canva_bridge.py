#!/usr/bin/env python3
"""
covibe-router/canva_bridge.py
==============================
Canva Marketing Asset Generator for Lore-Anchor

Generates marketing materials via Canva API:
- Feature announcement cards
- Social media posts (Twitter/Instagram)
- Product update banners
- Weekly metric infographics

Usage:
  python3 canva_bridge.py --type feature-card --title "C2PA署名機能" --description "..."
  python3 canva_bridge.py --type social-post --metric "waitlist=847"
  python3 canva_bridge.py --type kpi-infographic --supabase-url $SUPABASE_URL

Or trigger via Make.com webhook:
  POST http://localhost:8888/canva-generate
  { "type": "feature-card", "title": "...", "description": "..." }
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime, timezone, timedelta
from typing import Literal

import httpx

JST = timezone(timedelta(hours=9))

CANVA_API = "https://api.canva.com/rest/v1"

# Asset types and their Canva template mappings
# Replace template IDs with your actual Canva brand template IDs
TEMPLATE_MAP = {
    "feature-card": {
        "id": os.getenv("CANVA_TEMPLATE_FEATURE", ""),
        "description": "Feature announcement card (1080x1080)",
        "fields": ["headline", "subtext", "cta_text"],
    },
    "twitter-post": {
        "id": os.getenv("CANVA_TEMPLATE_TWITTER", ""),
        "description": "Twitter card (1600x900)",
        "fields": ["headline", "body_text", "username"],
    },
    "instagram-post": {
        "id": os.getenv("CANVA_TEMPLATE_INSTAGRAM", ""),
        "description": "Instagram post (1080x1080)",
        "fields": ["headline", "subtext"],
    },
    "kpi-card": {
        "id": os.getenv("CANVA_TEMPLATE_KPI", ""),
        "description": "Weekly KPI metrics card",
        "fields": ["metric_1", "metric_2", "metric_3", "week_label"],
    },
}


class CanvaBridge:
    def __init__(self, canva_token: str | None = None):
        self.token = canva_token or os.environ.get("CANVA_TOKEN", "")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def create_design_from_template(
        self,
        template_id: str,
        title: str,
        data: dict,
    ) -> dict:
        """Create a Canva design from a brand template with autofill."""
        autofill_data = {
            k: {"type": "text", "text": str(v)}
            for k, v in data.items()
        }

        payload = {
            "brand_template_id": template_id,
            "title": title,
            "data": autofill_data,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{CANVA_API}/autofills",
                json=payload,
                headers=self.headers,
            )
            if resp.status_code in (200, 201, 202):
                return resp.json()
            else:
                # Fallback: create blank design
                return await self.create_blank_design(title)

    async def create_blank_design(self, title: str, design_type: str = "social_media_post") -> dict:
        """Create a blank Canva design as fallback."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{CANVA_API}/designs",
                json={
                    "design_type": {"type": "preset", "name": design_type},
                    "title": title,
                },
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_design_url(self, design_id: str) -> str | None:
        """Get the edit URL for a Canva design."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{CANVA_API}/designs/{design_id}",
                headers=self.headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("design", {}).get("urls", {}).get("edit_url")
        return None

    async def export_design(self, design_id: str, format: str = "png") -> str | None:
        """Export design as image and return download URL."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Start export
            resp = await client.post(
                f"{CANVA_API}/exports",
                json={
                    "design_id": design_id,
                    "format": {"type": format},
                },
                headers=self.headers,
            )
            if resp.status_code not in (200, 201):
                return None

            export_id = resp.json().get("job", {}).get("id")
            if not export_id:
                return None

            # Poll for completion (max 30s)
            for _ in range(10):
                await asyncio.sleep(3)
                poll = await client.get(
                    f"{CANVA_API}/exports/{export_id}",
                    headers=self.headers,
                )
                job = poll.json().get("job", {})
                if job.get("status") == "success":
                    urls = job.get("urls", [])
                    return urls[0] if urls else None
                elif job.get("status") == "failed":
                    return None

        return None

    async def generate_feature_card(
        self,
        feature_name: str,
        description: str,
        cta: str = "ウェイティングリストに参加",
    ) -> dict:
        """Generate a feature announcement card."""
        template = TEMPLATE_MAP["feature-card"]
        title = f"feature-{feature_name.lower().replace(' ', '-')}-{datetime.now(JST).strftime('%Y%m%d')}"

        data = {
            "headline": feature_name[:30],
            "subtext": description[:60],
            "cta_text": cta[:20],
        }

        if template["id"]:
            result = await self.create_design_from_template(template["id"], title, data)
        else:
            result = await self.create_blank_design(title)

        design_id = (result.get("job", {}).get("result", {}).get("design", {}).get("id") or
                     result.get("design", {}).get("id", ""))
        edit_url = await self.get_design_url(design_id) if design_id else None

        return {
            "type": "feature-card",
            "design_id": design_id,
            "title": title,
            "edit_url": edit_url,
            "data": data,
        }

    async def generate_kpi_card(self, metrics: dict) -> dict:
        """Generate weekly KPI metrics card."""
        now = datetime.now(JST)
        week_label = f"Week of {now.strftime('%m/%d')}"
        title = f"kpi-{now.strftime('%Y-%m-%d')}"

        data = {
            "metric_1": f"ウェイトリスト: {metrics.get('waitlist', '?')}人",
            "metric_2": f"今週の登録: +{metrics.get('new_signups', '?')}人",
            "metric_3": f"目標達成率: {metrics.get('goal_pct', '?')}%",
            "week_label": week_label,
        }

        template = TEMPLATE_MAP["kpi-card"]
        if template["id"]:
            result = await self.create_design_from_template(template["id"], title, data)
        else:
            result = await self.create_blank_design(title)

        design_id = (result.get("job", {}).get("result", {}).get("design", {}).get("id") or
                     result.get("design", {}).get("id", ""))
        edit_url = await self.get_design_url(design_id) if design_id else None

        return {
            "type": "kpi-card",
            "design_id": design_id,
            "title": title,
            "edit_url": edit_url,
            "data": data,
        }


# ── FastAPI Router Extension ────────────────────────────────────────────────────
# This is imported by router.py to add Canva endpoints
from fastapi import APIRouter
from pydantic import BaseModel

canva_router = APIRouter(prefix="/canva", tags=["canva"])


class FeatureCardRequest(BaseModel):
    feature_name: str
    description: str
    cta: str = "ウェイティングリストに参加 →"


class KpiCardRequest(BaseModel):
    waitlist: int = 0
    new_signups: int = 0
    goal_pct: float = 0.0


@canva_router.post("/feature-card")
async def create_feature_card(req: FeatureCardRequest):
    bridge = CanvaBridge()
    result = await bridge.generate_feature_card(req.feature_name, req.description, req.cta)
    return result


@canva_router.post("/kpi-card")
async def create_kpi_card(req: KpiCardRequest):
    bridge = CanvaBridge()
    result = await bridge.generate_kpi_card({
        "waitlist": req.waitlist,
        "new_signups": req.new_signups,
        "goal_pct": round(req.goal_pct, 1),
    })
    return result


# ── CLI ────────────────────────────────────────────────────────────────────────
async def main():
    parser = argparse.ArgumentParser(description="Canva marketing asset generator")
    sub = parser.add_subparsers(dest="command")

    fc = sub.add_parser("feature-card", help="Generate feature announcement card")
    fc.add_argument("--title", required=True)
    fc.add_argument("--description", required=True)
    fc.add_argument("--cta", default="ウェイティングリストに参加")

    kpi = sub.add_parser("kpi-card", help="Generate KPI metrics card")
    kpi.add_argument("--waitlist", type=int, default=0)
    kpi.add_argument("--new-signups", type=int, default=0)
    kpi.add_argument("--goal-pct", type=float, default=0.0)

    args = parser.parse_args()
    bridge = CanvaBridge()

    if args.command == "feature-card":
        result = await bridge.generate_feature_card(args.title, args.description, args.cta)
    elif args.command == "kpi-card":
        result = await bridge.generate_kpi_card({
            "waitlist": args.waitlist,
            "new_signups": args.new_signups,
            "goal_pct": args.goal_pct,
        })
    else:
        parser.print_help()
        return

    print(json.dumps(result, indent=2, ensure_ascii=False))
    if url := result.get("edit_url"):
        print(f"\n🎨 Edit in Canva: {url}")


if __name__ == "__main__":
    asyncio.run(main())
