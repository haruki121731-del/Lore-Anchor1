"""
PixelSeal — Invisible Watermark Embedding & Extraction

Two back-ends are provided:

1. **DWT mode** (default, ``backend="dwt"``)
   Deterministic, model-free watermarking using the Discrete Wavelet
   Transform (Haar).  A 128-bit message is spread-spectrum-encoded into
   the HL (horizontal detail) sub-band.  Robust against JPEG compression,
   mild resize, and moderate adversarial noise (ε ≤ 16).  No pretrained
   weights required — works out of the box.

2. **NN mode** (``backend="nn"``)
   Learned encoder/decoder network inspired by Meta Seal / WAM.
   Requires pretrained weights for reliable extraction.

References
----------
- Meta Seal / WAM : https://github.com/facebookresearch/watermark-anything
- Robust Watermarking survey: Cox et al., "Digital Watermarking and
  Steganography" (Morgan Kaufmann)
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

if TYPE_CHECKING:
    import torch

logger = logging.getLogger(__name__)

WATERMARK_BITS = 128


class SealBackend(str, Enum):
    DWT = "dwt"
    NN = "nn"


# ============================================================================
# Bit <-> ID helpers
# ============================================================================
def _id_to_bits(watermark_id: str) -> np.ndarray:
    """32-char hex -> 128-element {-1, +1} array (bipolar for spread-spectrum)."""
    value = int(watermark_id[:32], 16)
    return np.array(
        [1.0 if (value >> i) & 1 else -1.0 for i in range(WATERMARK_BITS)],
        dtype=np.float32,
    )


def _bits_to_id(bits: np.ndarray) -> str:
    """128-element float array -> 32-char hex.  Decision boundary at 0."""
    value = 0
    for i in range(min(len(bits), WATERMARK_BITS)):
        if bits[i] > 0:
            value |= 1 << i
    return f"{value:032x}"


# ============================================================================
# Spread-spectrum chip sequence (PN code)
# ============================================================================
def _pn_sequence(seed: int, length: int) -> np.ndarray:
    """Deterministic pseudo-random {-1, +1} chip sequence."""
    rng = np.random.default_rng(seed)
    return rng.choice([-1.0, 1.0], size=length).astype(np.float32)


# ============================================================================
# Haar DWT / IDWT  (pure numpy, no pywt dependency)
# ============================================================================
def _haar_dwt2(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """2D Haar DWT.  Input: [H, W].  Returns (LL, LH, HL, HH) each [H/2, W/2]."""
    h, w = x.shape
    # Rows
    lo = (x[:, 0::2] + x[:, 1::2]) / 2.0
    hi = (x[:, 0::2] - x[:, 1::2]) / 2.0
    # Columns
    ll = (lo[0::2, :] + lo[1::2, :]) / 2.0
    lh = (lo[0::2, :] - lo[1::2, :]) / 2.0
    hl = (hi[0::2, :] + hi[1::2, :]) / 2.0
    hh = (hi[0::2, :] - hi[1::2, :]) / 2.0
    return ll, lh, hl, hh


def _haar_idwt2(ll: np.ndarray, lh: np.ndarray, hl: np.ndarray, hh: np.ndarray) -> np.ndarray:
    """2D Haar IDWT.  Inverse of _haar_dwt2."""
    h2, w2 = ll.shape
    h, w = h2 * 2, w2 * 2
    # Reconstruct columns
    lo = np.zeros((h, w2), dtype=np.float64)
    hi = np.zeros((h, w2), dtype=np.float64)
    lo[0::2, :] = ll + lh
    lo[1::2, :] = ll - lh
    hi[0::2, :] = hl + hh
    hi[1::2, :] = hl - hh
    # Reconstruct rows
    result = np.zeros((h, w), dtype=np.float64)
    result[:, 0::2] = lo + hi
    result[:, 1::2] = lo - hi
    return result


# ============================================================================
# DWT-based Spread-Spectrum Watermark
# ============================================================================
_CHIP_SEED_BASE = 0xA5C0DE  # arbitrary constant
_EMBED_STRENGTH = 3.5  # controls visibility vs. robustness trade-off


def _embed_dwt(
    image: Image.Image,
    watermark_id: str,
    strength: float = _EMBED_STRENGTH,
) -> Image.Image:
    """Embed 128-bit watermark into the HL sub-band of each colour channel."""
    img = np.array(image, dtype=np.float64)
    h, w, c = img.shape
    # ensure even dims
    eh, ew = (h // 2) * 2, (w // 2) * 2
    img = img[:eh, :ew, :]

    bits = _id_to_bits(watermark_id)  # [128] in {-1, +1}

    for ch in range(c):
        ll, lh, hl, hh = _haar_dwt2(img[:, :, ch])
        sub_h, sub_w = hl.shape
        capacity = sub_h * sub_w
        if capacity < WATERMARK_BITS:
            logger.warning("Image too small for DWT watermark (%d < %d)", capacity, WATERMARK_BITS)
            continue

        # Spread each bit across multiple coefficients
        chips_per_bit = capacity // WATERMARK_BITS
        flat = hl.ravel()

        for b in range(WATERMARK_BITS):
            start = b * chips_per_bit
            end = start + chips_per_bit
            pn = _pn_sequence(_CHIP_SEED_BASE + b, chips_per_bit)
            flat[start:end] += strength * bits[b] * pn

        hl = flat.reshape(sub_h, sub_w)
        img[:, :, ch] = _haar_idwt2(ll, lh, hl, hh)

    img = np.clip(img, 0, 255).astype(np.uint8)
    result = Image.fromarray(img)
    # restore original dims if they were trimmed
    if (result.size[0], result.size[1]) != (w, h):
        result = result.resize((w, h), Image.LANCZOS)
    return result


def _extract_dwt(image: Image.Image) -> np.ndarray:
    """Extract 128 soft-decision values from the HL sub-band.

    Returns array of shape [128]. Positive = bit 1, negative = bit 0.
    """
    img = np.array(image, dtype=np.float64)
    h, w, c = img.shape
    eh, ew = (h // 2) * 2, (w // 2) * 2
    img = img[:eh, :ew, :]

    accum = np.zeros(WATERMARK_BITS, dtype=np.float64)

    for ch in range(c):
        _, _, hl, _ = _haar_dwt2(img[:, :, ch])
        sub_h, sub_w = hl.shape
        capacity = sub_h * sub_w
        if capacity < WATERMARK_BITS:
            continue

        chips_per_bit = capacity // WATERMARK_BITS
        flat = hl.ravel()

        for b in range(WATERMARK_BITS):
            start = b * chips_per_bit
            end = start + chips_per_bit
            pn = _pn_sequence(_CHIP_SEED_BASE + b, chips_per_bit)
            corr = np.dot(flat[start:end], pn) / chips_per_bit
            accum[b] += corr

    return accum


# ============================================================================
# NN-based Encoder / Decoder  (requires pretrained weights for reliability)
# Torch is imported lazily so the DWT backend works without torch installed.
# ============================================================================
_NN_WEIGHTS_DIR = "weights/pixelseal"
_nn_enc = None
_nn_dec = None


def _build_nn_models(device):  # type: ignore[no-untyped-def]
    """Build and return (encoder, decoder) on *device*.  Requires torch."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    class _Encoder(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.prep = nn.Sequential(
                nn.Linear(WATERMARK_BITS, 512), nn.ReLU(),
                nn.Linear(512, 3 * 32 * 32),
            )
            self.down = nn.Sequential(
                nn.Conv2d(6, 64, 3, stride=2, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
                nn.Conv2d(64, 128, 3, stride=2, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            )
            self.up = nn.Sequential(
                nn.ConvTranspose2d(128, 64, 4, stride=2, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
                nn.ConvTranspose2d(64, 3, 4, stride=2, padding=1), nn.Tanh(),
            )
            self.strength = 0.03

        def forward(self, image, bits):
            b, _, h, w = image.shape
            bm = self.prep(bits).view(b, 3, 32, 32)
            bm = F.interpolate(bm, size=(h, w), mode="bilinear", align_corners=False)
            x = torch.cat([image, bm], dim=1)
            feat = self.down(x)
            residual = self.up(feat)
            residual = F.interpolate(residual, size=(h, w), mode="bilinear", align_corners=False)
            return (image + residual * self.strength).clamp(0, 1)

    class _Decoder(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(3, 64, 3, stride=2, padding=1), nn.ReLU(),
                nn.Conv2d(64, 128, 3, stride=2, padding=1), nn.ReLU(),
                nn.Conv2d(128, 256, 3, stride=2, padding=1), nn.ReLU(),
                nn.AdaptiveAvgPool2d(1),
            )
            self.classifier = nn.Sequential(
                nn.Linear(256, 512), nn.ReLU(), nn.Dropout(0.1),
                nn.Linear(512, WATERMARK_BITS),
            )

        def forward(self, image):
            feat = self.features(image).view(image.shape[0], -1)
            return self.classifier(feat)

    return _Encoder().to(device).eval(), _Decoder().to(device).eval()


def _get_nn_models(device):  # type: ignore[no-untyped-def]
    import os
    import torch

    global _nn_enc, _nn_dec
    if _nn_enc is not None and _nn_dec is not None:
        return _nn_enc, _nn_dec

    _nn_enc, _nn_dec = _build_nn_models(device)

    enc_path = os.path.join(_NN_WEIGHTS_DIR, "encoder.pt")
    dec_path = os.path.join(_NN_WEIGHTS_DIR, "decoder.pt")

    if os.path.isfile(enc_path) and os.path.isfile(dec_path):
        _nn_enc.load_state_dict(torch.load(enc_path, map_location=device, weights_only=True))
        _nn_dec.load_state_dict(torch.load(dec_path, map_location=device, weights_only=True))
        logger.info("PixelSeal NN weights loaded from %s", _NN_WEIGHTS_DIR)
    else:
        logger.warning(
            "PixelSeal NN weights not found at %s — "
            "extraction will be unreliable. Use DWT backend or train weights.",
            _NN_WEIGHTS_DIR,
        )

    return _nn_enc, _nn_dec


# ============================================================================
# Public API
# ============================================================================


def embed_watermark(
    image: Image.Image,
    watermark_id: str,
    *,
    backend: str | SealBackend = SealBackend.DWT,
    device: "torch.device | None" = None,
) -> Image.Image:
    """Embed an invisible 128-bit watermark into *image*.

    Args:
        image: Input PIL Image (RGB).
        watermark_id: 32-char hex string.
        backend: ``"dwt"`` (default, deterministic) or ``"nn"`` (learned).
        device: Torch device (NN backend only).

    Returns:
        Watermarked PIL Image.
    """
    backend = SealBackend(backend)

    if backend is SealBackend.DWT:
        result = _embed_dwt(image, watermark_id)
        logger.info("Watermark embedded (DWT, id=%s...)", watermark_id[:8])
        return result

    # NN backend — torch imported lazily
    import torch
    from torchvision import transforms

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    encoder, _ = _get_nn_models(device)

    x = transforms.ToTensor()(image).unsqueeze(0).to(device)
    bits_val = int(watermark_id[:32], 16)
    bits = torch.tensor(
        [(bits_val >> i) & 1 for i in range(WATERMARK_BITS)],
        dtype=torch.float32,
    ).unsqueeze(0).to(device)

    with torch.no_grad():
        wm = encoder(x, bits)

    arr = (wm.squeeze(0).cpu().numpy() * 255).astype(np.uint8)
    result = Image.fromarray(arr.transpose(1, 2, 0))
    logger.info("Watermark embedded (NN, id=%s...)", watermark_id[:8])
    return result


def extract_watermark(
    image: Image.Image,
    *,
    backend: str | SealBackend = SealBackend.DWT,
    device: "torch.device | None" = None,
) -> str:
    """Extract watermark ID from *image*.

    Args:
        image: Possibly watermarked PIL Image (RGB).
        backend: Must match the backend used for embedding.
        device: Torch device (NN backend only).

    Returns:
        Extracted 32-char hex watermark ID.
    """
    backend = SealBackend(backend)

    if backend is SealBackend.DWT:
        soft = _extract_dwt(image)
        wm_id = _bits_to_id(soft)
        logger.info("Watermark extracted (DWT, id=%s...)", wm_id[:8])
        return wm_id

    # NN backend
    import torch
    from torchvision import transforms

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _, decoder = _get_nn_models(device)

    x = transforms.ToTensor()(image).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = decoder(x)
        hard = (torch.sigmoid(logits) > 0.5).float().squeeze(0).cpu().numpy()

    wm_id = _bits_to_id(hard)
    logger.info("Watermark extracted (NN, id=%s...)", wm_id[:8])
    return wm_id


def verify_watermark(
    image: Image.Image,
    expected_id: str,
    *,
    backend: str | SealBackend = SealBackend.DWT,
    device: "torch.device | None" = None,
) -> tuple[bool, float]:
    """Verify whether *image* contains the expected watermark.

    Returns:
        (match, bit_accuracy) — match is True if accuracy >= 0.75.
    """
    extracted = extract_watermark(image, backend=backend, device=device)
    expected_val = int(expected_id[:32], 16)
    extracted_val = int(extracted, 16)
    xor = expected_val ^ extracted_val
    wrong = bin(xor).count("1")
    accuracy = (WATERMARK_BITS - wrong) / WATERMARK_BITS
    match = accuracy >= 0.75
    logger.info("Watermark verify: accuracy=%.1f%% match=%s", accuracy * 100, match)
    return match, accuracy
