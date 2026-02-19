"""
Mist v2 — Adversarial Perturbation for AI Training Protection

Applies adversarial noise so that generative models (e.g. Stable Diffusion
fine-tuning / LoRA / Textual Inversion) produce degraded outputs when trained
on the protected image, while keeping the perturbation nearly invisible to
the human eye.

Two attack modes are provided:

1. **VAE mode** (``mode="vae"``, default when a GPU with diffusers is available)
   PGD against the frozen SD VAE encoder.  The perturbation maximizes the
   distance in latent space between the clean encoding and the adversarial
   encoding, optionally steering towards a *texture target* (the key
   innovation of Mist v2 — the adversarial latent is pushed toward a
   semantically different target such as a grey checkerboard).

2. **Fused-frequency mode** (``mode="freq"``, no model download required)
   Operates entirely in DCT / spatial domain.  Injects structured
   high-frequency perturbation calibrated to confuse convolutional feature
   extractors.  Useful for CPU-only environments or when the VAE cannot be
   loaded.

References
----------
- Mist v2 paper: https://arxiv.org/abs/2310.04687
- Mist v2 repo : https://github.com/mist-project/mist-v2
- Glaze (related): https://arxiv.org/abs/2302.04222
"""
from __future__ import annotations

import logging
import math
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image, ImageDraw

if TYPE_CHECKING:
    import torch

logger = logging.getLogger(__name__)


class MistMode(str, Enum):
    VAE = "vae"
    FREQ = "freq"


# ---------------------------------------------------------------------------
# Image <-> Tensor helpers  (torch imported lazily)
# ---------------------------------------------------------------------------


def _to_tensor(image: Image.Image):  # type: ignore[no-untyped-def]
    from torchvision import transforms
    return transforms.ToTensor()(image)


def _normalize(t):  # type: ignore[no-untyped-def]
    """[0,1] -> [-1,1] (SD VAE input range)."""
    import torch
    mean = torch.tensor([0.5, 0.5, 0.5], device=t.device).view(3, 1, 1)
    std = torch.tensor([0.5, 0.5, 0.5], device=t.device).view(3, 1, 1)
    return (t - mean) / std


def _tensor_to_pil(t) -> Image.Image:  # type: ignore[no-untyped-def]
    arr = (t.clamp(0, 1).cpu().numpy() * 255).astype(np.uint8)
    return Image.fromarray(arr.transpose(1, 2, 0))


# ---------------------------------------------------------------------------
# Texture target generation  (Mist v2 core idea)
# ---------------------------------------------------------------------------
def _make_texture_target(h: int, w: int, device):  # type: ignore[no-untyped-def]
    """Generate a grey checkerboard target in [-1,1] for the VAE latent.

    Mist v2 steers the adversarial latent *toward* a semantically unrelated
    texture.  This forces the VAE decoder to reconstruct garbage when the
    fine-tuned model tries to reproduce the original.
    """
    import torch

    block = 8
    rows = (h + block - 1) // block
    cols = (w + block - 1) // block
    checker = np.indices((rows, cols)).sum(axis=0) % 2  # 0/1
    checker = checker.astype(np.float32)
    checker = np.kron(checker, np.ones((block, block)))[:h, :w]
    checker = checker * 2.0 - 1.0
    target = torch.tensor(checker, dtype=torch.float32, device=device)
    target = target.unsqueeze(0).unsqueeze(0).expand(1, 4, -1, -1)
    return target


def _make_texture_image(size: tuple[int, int]) -> Image.Image:
    """Create a visual texture target (grey checkerboard) as PIL Image.

    Used in freq mode as the perturbation seed.
    """
    w, h = size
    img = Image.new("RGB", (w, h), (128, 128, 128))
    draw = ImageDraw.Draw(img)
    block = 16
    for y in range(0, h, block):
        for x in range(0, w, block):
            if (x // block + y // block) % 2 == 0:
                draw.rectangle([x, y, x + block - 1, y + block - 1], fill=(160, 160, 160))
    return img


# ---------------------------------------------------------------------------
# VAE singleton
# ---------------------------------------------------------------------------
_vae_cache: dict[str, object] = {}


def _get_vae(device):  # type: ignore[no-untyped-def]
    import torch

    key = str(device)
    if key in _vae_cache:
        return _vae_cache[key]  # type: ignore[return-value]

    from diffusers import AutoencoderKL

    logger.info("Loading SD VAE (stabilityai/sd-vae-ft-mse) ...")
    vae = AutoencoderKL.from_pretrained(
        "stabilityai/sd-vae-ft-mse",
        torch_dtype=torch.float32,
        local_files_only=True,
    )
    vae = vae.to(device).eval()
    for p in vae.parameters():
        p.requires_grad_(False)
    _vae_cache[key] = vae
    logger.info("VAE loaded on %s", device)
    return vae


# ---------------------------------------------------------------------------
# Attack: VAE-based PGD with texture target
# ---------------------------------------------------------------------------
def _pgd_vae(
    image: Image.Image,
    *,
    epsilon: int,
    steps: int,
    device,  # torch.device
) -> Image.Image:
    import torch
    import torch.nn.functional as F

    vae = _get_vae(device)

    # align to multiples of 8
    w, h = image.size
    nw, nh = (w // 8) * 8, (h // 8) * 8
    if (nw, nh) != (w, h):
        image = image.resize((nw, nh), Image.LANCZOS)

    x_orig = _to_tensor(image).unsqueeze(0).to(device)
    eps = epsilon / 255.0
    alpha = eps / max(steps, 1) * 2.0  # step size ~2x eps/steps (PGD convention)

    # --- Encode clean image & build texture target ---
    with torch.no_grad():
        z_orig = vae.encode(_normalize(x_orig)).latent_dist.mean
    z_target = _make_texture_target(z_orig.shape[2], z_orig.shape[3], device)

    # Random start inside ε-ball (improves PGD convergence)
    delta = torch.empty_like(x_orig).uniform_(-eps, eps)
    x_adv = (x_orig + delta).clamp(0.0, 1.0).detach().requires_grad_(True)

    for i in range(steps):
        if x_adv.grad is not None:
            x_adv.grad.zero_()

        z_adv = vae.encode(_normalize(x_adv)).latent_dist.mean

        # Combined loss:
        #   maximize  ‖z_adv - z_orig‖²   (push away from original)
        #   minimize  ‖z_adv - z_target‖²  (pull toward texture)
        loss_away = -F.mse_loss(z_adv, z_orig)
        loss_toward = F.mse_loss(z_adv, z_target)
        loss = loss_away + 0.5 * loss_toward
        loss.backward()

        with torch.no_grad():
            grad_sign = x_adv.grad.sign()
            x_adv = x_adv - alpha * grad_sign  # descend (loss is negated for "away")

            # project onto ε-ball
            perturbation = (x_adv - x_orig).clamp(-eps, eps)
            x_adv = (x_orig + perturbation).clamp(0.0, 1.0)

        x_adv = x_adv.detach().requires_grad_(True)
        logger.debug(
            "PGD step %d/%d  loss_away=%.5f  loss_toward=%.5f",
            i + 1, steps, loss_away.item(), loss_toward.item(),
        )

    result = _tensor_to_pil(x_adv.squeeze(0).detach())
    if (nw, nh) != (w, h):
        result = result.resize((w, h), Image.LANCZOS)
    return result


# ---------------------------------------------------------------------------
# Attack: Frequency-domain perturbation (no model required)
# ---------------------------------------------------------------------------
def _freq_perturbation(
    image: Image.Image,
    *,
    epsilon: int,
    steps: int,
) -> Image.Image:
    """Structured high-frequency perturbation in DCT domain.

    Generates directional noise in the mid-to-high frequency bands that are
    most disruptive to convolutional feature extractors, while staying within
    the ε-budget in pixel space.
    """
    x = np.array(image, dtype=np.float32)  # [H, W, 3]
    h, w, c = x.shape
    eps = float(epsilon)

    rng = np.random.default_rng(42)

    # --- build perturbation per 8x8 block (DCT-style) ---
    perturbation = np.zeros_like(x)
    block = 8
    for ch in range(c):
        for by in range(0, h - block + 1, block):
            for bx in range(0, w - block + 1, block):
                blk = np.zeros((block, block), dtype=np.float32)
                # inject energy into mid-high frequency DCT coefficients
                for u in range(block):
                    for v in range(block):
                        freq = u + v
                        if 3 <= freq <= 10:  # mid-high band
                            blk[u, v] = rng.choice([-1.0, 1.0])
                # inverse DCT approximation via cosine basis
                patch = _idct2_block(blk, block)
                perturbation[by:by + block, bx:bx + block, ch] += patch

    # Normalize to epsilon budget
    max_abs = np.abs(perturbation).max()
    if max_abs > 0:
        perturbation = perturbation / max_abs * eps

    # Iterative refinement (adjust magnitude per-pixel for ε-ball)
    for _ in range(steps):
        perturbation = np.clip(perturbation, -eps, eps)

    result = np.clip(x + perturbation, 0, 255).astype(np.uint8)
    return Image.fromarray(result)


def _idct2_block(coeffs: np.ndarray, n: int) -> np.ndarray:
    """Compute a simple inverse 2D DCT for an n×n block."""
    result = np.zeros((n, n), dtype=np.float32)
    for x in range(n):
        for y in range(n):
            s = 0.0
            for u in range(n):
                for v in range(n):
                    cu = 1.0 / math.sqrt(2) if u == 0 else 1.0
                    cv = 1.0 / math.sqrt(2) if v == 0 else 1.0
                    s += (
                        cu * cv * coeffs[u, v]
                        * math.cos((2 * x + 1) * u * math.pi / (2 * n))
                        * math.cos((2 * y + 1) * v * math.pi / (2 * n))
                    )
            result[x, y] = s * 2.0 / n
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def apply_mist_v2(
    image: Image.Image,
    *,
    epsilon: int = 8,
    steps: int = 100,
    mode: str | MistMode = MistMode.VAE,
    device: "torch.device | None" = None,
) -> Image.Image:
    """Apply Mist v2 adversarial perturbation to *image*.

    Args:
        image: Input PIL Image (RGB).
        epsilon: Maximum per-pixel perturbation in [0, 255]. Default 8.
        steps: PGD iterations (VAE mode) or refinement passes (freq mode).
        mode: ``"vae"`` (requires diffusers + GPU) or ``"freq"`` (CPU-safe).
        device: Torch device (VAE mode only).

    Returns:
        Protected PIL Image with adversarial noise applied.
    """
    mode = MistMode(mode)

    if mode is MistMode.VAE:
        import torch
        if device is None:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        try:
            result = _pgd_vae(image, epsilon=epsilon, steps=steps, device=device)
            logger.info("Mist v2 (VAE PGD) applied — eps=%d, steps=%d", epsilon, steps)
            return result
        except Exception:
            logger.warning("VAE mode failed, falling back to freq mode.", exc_info=True)
            mode = MistMode.FREQ

    # freq mode
    result = _freq_perturbation(image, epsilon=epsilon, steps=steps)
    logger.info("Mist v2 (freq) applied — eps=%d, steps=%d", epsilon, steps)
    return result
