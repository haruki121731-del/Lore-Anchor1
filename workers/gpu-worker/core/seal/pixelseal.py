"""
PixelSeal — Invisible Watermark Embedding & Extraction

Embeds a 128-bit identifier into an image using a learned encoder/decoder
network. The watermark is designed to survive common image transformations
(JPEG compression, resize, crop, adversarial noise).

This module provides a simplified implementation inspired by Meta's Seal
(https://github.com/facebookresearch/watermark-anything). In production,
replace with the full pretrained model weights.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Watermark ID encoding helpers
# ---------------------------------------------------------------------------
WATERMARK_BITS = 128


def _id_to_bits(watermark_id: str) -> torch.Tensor:
    """Convert a hex watermark ID (32 chars = 128 bits) to a binary tensor."""
    value = int(watermark_id[:32], 16)
    bits = [(value >> i) & 1 for i in range(WATERMARK_BITS)]
    return torch.tensor(bits, dtype=torch.float32)


def _bits_to_id(bits: torch.Tensor) -> str:
    """Convert a binary tensor back to a hex watermark ID."""
    value = 0
    for i, b in enumerate(bits):
        if b > 0.5:
            value |= 1 << i
    return f"{value:032x}"


# ---------------------------------------------------------------------------
# Lightweight Encoder / Decoder networks
# ---------------------------------------------------------------------------
class WatermarkEncoder(nn.Module):
    """Embeds a 128-bit message into an image via additive residual."""

    def __init__(self) -> None:
        super().__init__()
        # Project the bit-string to spatial feature maps
        self.bit_proj = nn.Sequential(
            nn.Linear(WATERMARK_BITS, 256),
            nn.ReLU(),
            nn.Linear(256, 3 * 16 * 16),
        )
        # UNet-like conv stack to produce residual
        self.conv = nn.Sequential(
            nn.Conv2d(6, 64, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 64, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 3, 3, padding=1),
            nn.Tanh(),
        )
        self.strength = 0.02  # controls watermark visibility

    def forward(self, image: torch.Tensor, bits: torch.Tensor) -> torch.Tensor:
        """
        Args:
            image: [B, 3, H, W] in [0, 1]
            bits:  [B, 128]
        Returns:
            watermarked image [B, 3, H, W]
        """
        b, _, h, w = image.shape
        bit_map = self.bit_proj(bits).view(b, 3, 16, 16)
        bit_map = F.interpolate(bit_map, size=(h, w), mode="bilinear", align_corners=False)
        combined = torch.cat([image, bit_map], dim=1)  # [B, 6, H, W]
        residual = self.conv(combined) * self.strength
        return (image + residual).clamp(0, 1)


class WatermarkDecoder(nn.Module):
    """Extracts a 128-bit message from a (possibly distorted) image."""

    def __init__(self) -> None:
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(3, 64, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 64, 3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )
        self.fc = nn.Sequential(
            nn.Linear(64, 256),
            nn.ReLU(),
            nn.Linear(256, WATERMARK_BITS),
        )

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        Args:
            image: [B, 3, H, W]
        Returns:
            logits [B, 128] — apply sigmoid to get bit probabilities.
        """
        feat = self.conv(image).view(image.shape[0], -1)
        return self.fc(feat)


# ---------------------------------------------------------------------------
# Model loader (lazy singleton)
# ---------------------------------------------------------------------------
_encoder: WatermarkEncoder | None = None
_decoder: WatermarkDecoder | None = None

MODEL_WEIGHTS_PATH = "weights/pixelseal"


def _get_models(device: torch.device) -> tuple[WatermarkEncoder, WatermarkDecoder]:
    """Load or initialize PixelSeal encoder/decoder."""
    global _encoder, _decoder
    if _encoder is not None and _decoder is not None:
        return _encoder, _decoder

    _encoder = WatermarkEncoder().to(device).eval()
    _decoder = WatermarkDecoder().to(device).eval()

    # TODO: Load pretrained weights when available:
    # _encoder.load_state_dict(torch.load(f"{MODEL_WEIGHTS_PATH}/encoder.pt"))
    # _decoder.load_state_dict(torch.load(f"{MODEL_WEIGHTS_PATH}/decoder.pt"))
    logger.warning(
        "PixelSeal: Using randomly initialized weights. "
        "Replace with pretrained weights for production use."
    )

    return _encoder, _decoder


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_to_tensor = transforms.ToTensor()


def embed_watermark(
    image: Image.Image,
    watermark_id: str,
    *,
    device: torch.device | None = None,
) -> Image.Image:
    """Embed an invisible watermark into *image*.

    Args:
        image: Input PIL Image (RGB).
        watermark_id: 32-char hex string (128-bit identifier).
        device: Torch device.

    Returns:
        Watermarked PIL Image.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    encoder, _ = _get_models(device)

    x = _to_tensor(image).unsqueeze(0).to(device)
    bits = _id_to_bits(watermark_id).unsqueeze(0).to(device)

    with torch.no_grad():
        watermarked = encoder(x, bits)

    arr = (watermarked.squeeze(0).cpu().numpy() * 255).astype(np.uint8)
    result = Image.fromarray(arr.transpose(1, 2, 0))

    logger.info("PixelSeal watermark embedded (id=%s...)", watermark_id[:8])
    return result


def extract_watermark(
    image: Image.Image,
    *,
    device: torch.device | None = None,
) -> str:
    """Extract watermark ID from an image.

    Args:
        image: Possibly watermarked PIL Image (RGB).
        device: Torch device.

    Returns:
        Extracted 32-char hex watermark ID.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    _, decoder = _get_models(device)

    x = _to_tensor(image).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = decoder(x)
        bits = (torch.sigmoid(logits) > 0.5).float().squeeze(0)

    extracted_id = _bits_to_id(bits)
    logger.info("PixelSeal watermark extracted (id=%s...)", extracted_id[:8])
    return extracted_id
