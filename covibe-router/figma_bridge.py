#!/usr/bin/env python3
"""
covibe-router/figma_bridge.py
==============================
Figma → Code Bridge for Lore-Anchor

Fetches Figma design specs and generates React/TypeScript components
using the local LLM (Ollama) or Claude depending on complexity.

Usage:
  python3 figma_bridge.py <figma_url> [--component-name MyComponent] [--dry-run]

  Or as a module:
    from figma_bridge import FigmaBridge
    bridge = FigmaBridge(figma_token="figd_...")
    component = await bridge.generate_component(figma_url, "ProtectionBadge")
"""

import os
import sys
import json
import asyncio
import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

# ── Config ─────────────────────────────────────────────────────────────────────
FIGMA_API = "https://api.figma.com/v1"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

REACT_SYSTEM_PROMPT = """You are an expert React/Next.js engineer for Lore-Anchor (AI protection SaaS for Japanese illustrators).
Stack: Next.js 14 App Router, TypeScript, Tailwind CSS, Framer Motion, shadcn/ui.
Design style: clean, professional, trust-inspiring. Japanese creator audience.
Output ONLY valid TypeScript/TSX code. No explanations."""


@dataclass
class FigmaComponent:
    name: str
    node_id: str
    width: float
    height: float
    fills: list
    children: list
    styles: dict


class FigmaBridge:
    def __init__(self, figma_token: str | None = None):
        self.token = figma_token or os.environ.get("FIGMA_TOKEN", "")
        self.headers = {"X-Figma-Token": self.token}

    def parse_figma_url(self, url: str) -> tuple[str, str]:
        """Extract file_key and node_id from Figma URL."""
        # https://www.figma.com/design/FILE_KEY/name?node-id=1-2
        # https://www.figma.com/file/FILE_KEY/name?node-id=1-2
        match = re.search(r'/(?:design|file)/([A-Za-z0-9]+)/', url)
        if not match:
            raise ValueError(f"Cannot parse Figma URL: {url}")
        file_key = match.group(1)

        node_match = re.search(r'node-id=([^&]+)', url)
        node_id = node_match.group(1).replace("-", ":") if node_match else "0:1"
        return file_key, node_id

    async def fetch_node(self, file_key: str, node_id: str) -> dict:
        """Fetch node data from Figma API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{FIGMA_API}/files/{file_key}/nodes",
                params={"ids": node_id},
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()
            nodes = data.get("nodes", {})
            key = node_id.replace("-", ":") if ":" not in node_id else node_id
            return nodes.get(key, {}).get("document", {})

    async def fetch_image(self, file_key: str, node_id: str) -> str | None:
        """Get PNG image URL for a node."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{FIGMA_API}/images/{file_key}",
                params={"ids": node_id, "format": "png", "scale": "2"},
                headers=self.headers,
            )
            if resp.status_code == 200:
                images = resp.json().get("images", {})
                return images.get(node_id.replace("-", ":")) or images.get(node_id)
        return None

    def summarize_node(self, node: dict, depth: int = 0) -> str:
        """Summarize Figma node structure for LLM context."""
        if depth > 4:
            return ""

        lines = []
        indent = "  " * depth
        name = node.get("name", "unnamed")
        node_type = node.get("type", "")

        # Collect relevant properties
        props = []
        if bbox := node.get("absoluteBoundingBox"):
            props.append(f"w={bbox['width']:.0f} h={bbox['height']:.0f}")
        if fills := node.get("fills", []):
            for fill in fills[:1]:
                if fill.get("type") == "SOLID":
                    c = fill.get("color", {})
                    props.append(f"fill=rgb({c.get('r',0)*255:.0f},{c.get('g',0)*255:.0f},{c.get('b',0)*255:.0f})")
        if chars := node.get("characters"):
            props.append(f'text="{chars[:30]}"')
        if style := node.get("style", {}):
            if fs := style.get("fontSize"):
                props.append(f"fontSize={fs}")
            if fw := style.get("fontWeight"):
                props.append(f"fontWeight={fw}")

        prop_str = f" [{', '.join(props)}]" if props else ""
        lines.append(f"{indent}{node_type}: {name}{prop_str}")

        for child in node.get("children", [])[:8]:
            lines.append(self.summarize_node(child, depth + 1))

        return "\n".join(filter(None, lines))

    async def generate_with_ollama(self, prompt: str) -> str:
        """Generate code using local Ollama."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": f"<system>{REACT_SYSTEM_PROMPT}</system>\n\n{prompt}",
                    "stream": False,
                    "options": {"temperature": 0.15, "top_p": 0.9},
                },
            )
            resp.raise_for_status()
            return resp.json().get("response", "")

    async def generate_with_claude(self, prompt: str, image_url: str | None = None) -> str:
        """Generate code using Claude (for complex/visual components)."""
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

        content = []
        if image_url:
            # Download image and send as base64
            async with httpx.AsyncClient(timeout=30.0) as http:
                img_resp = await http.get(image_url)
                img_b64 = __import__("base64").b64encode(img_resp.content).decode()
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
            })
        content.append({"type": "text", "text": prompt})

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=REACT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
        return message.content[0].text

    async def generate_component(
        self,
        figma_url: str,
        component_name: str,
        use_vision: bool = False,
    ) -> dict:
        """Main method: Figma URL → React component code."""
        print(f"Fetching Figma design for {component_name}...")
        file_key, node_id = self.parse_figma_url(figma_url)

        node = await self.fetch_node(file_key, node_id)
        if not node:
            raise ValueError(f"Node not found: {node_id}")

        design_summary = self.summarize_node(node)
        image_url = None

        if use_vision:
            print("Fetching Figma screenshot...")
            image_url = await self.fetch_image(file_key, node_id)

        prompt = f"""Generate a React/TypeScript component from this Figma design.

Component name: {component_name}

Figma design structure:
{design_summary}

Requirements:
- Use Next.js 14 App Router conventions
- TypeScript with proper Props interface
- Tailwind CSS for styling (match Figma colors/spacing exactly)
- Add 'use client' if interactive
- Framer Motion for any animations
- Accessible (aria labels, semantic HTML)
- Mobile responsive

Return complete component code starting with imports."""

        if use_vision and image_url:
            print(f"Using Claude Vision (image: {image_url[:50]}...)")
            code = await self.generate_with_claude(prompt, image_url)
        else:
            print(f"Using Ollama {OLLAMA_MODEL} (local, free)...")
            code = await self.generate_with_ollama(prompt)

        return {
            "component_name": component_name,
            "figma_url": figma_url,
            "node_id": node_id,
            "design_summary": design_summary,
            "code": code,
            "model": "claude-sonnet" if use_vision else OLLAMA_MODEL,
            "cost": 0.0 if not use_vision else None,
            "suggested_path": f"apps/web/components/{component_name}.tsx",
        }


async def main():
    parser = argparse.ArgumentParser(description="Figma → React component generator")
    parser.add_argument("figma_url", help="Figma design URL")
    parser.add_argument("--component-name", "-n", default="GeneratedComponent")
    parser.add_argument("--vision", action="store_true", help="Use Claude Vision (better but costs $)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    token = os.environ.get("FIGMA_TOKEN", "")
    if not token and not args.dry_run:
        print("Error: FIGMA_TOKEN env var required")
        sys.exit(1)

    bridge = FigmaBridge(figma_token=token)

    if args.dry_run:
        print(f"[DRY RUN] Would generate: {args.component_name} from {args.figma_url}")
        return

    result = await bridge.generate_component(
        args.figma_url,
        args.component_name,
        use_vision=args.vision,
    )

    print(f"\n{'='*60}")
    print(f"Component: {result['component_name']}")
    print(f"Model: {result['model']} | Cost: {'$0.00 (local)' if result['cost'] == 0 else 'API'}")
    print(f"Suggested path: {result['suggested_path']}")
    print(f"{'='*60}\n")

    if args.output:
        Path(args.output).write_text(result["code"])
        print(f"Written to: {args.output}")
    else:
        print(result["code"])


if __name__ == "__main__":
    asyncio.run(main())
