"""
Mist v2 — Adversarial Perturbation for AI Training Protection

Applies adversarial noise to an image so that generative models (e.g. Stable
Diffusion fine-tuning) produce degraded outputs when trained on the protected
image, while keeping the perturbation nearly invisible to the human eye.

The approach uses PGD (Projected Gradient Descent) against a frozen VAE encoder
from Stable Diffusion to maximize the encoding error.

Reference: https://github.com/mist-project/mist-v2
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Image <-> Tensor helpers
# ---------------------------------------------------------------------------
_to_tensor = transforms.Compose([
    transforms.ToTensor(),  # [0, 255] -> [0.0, 1.0]
])

_IMAGENET_MEAN = torch.tensor([0.5, 0.5, 0.5]).view(3, 1, 1)
_IMAGENET_STD = torch.tensor([0.5, 0.5, 0.5]).view(3, 1, 1)


def _normalize(t: torch.Tensor) -> torch.Tensor:
    """Normalize tensor from [0,1] to [-1,1] (SD VAE expected range)."""
    return (t - _IMAGENET_MEAN.to(t.device)) / _IMAGENET_STD.to(t.device)


def _denormalize(t: torch.Tensor) -> torch.Tensor:
    """Denormalize tensor from [-1,1] back to [0,1]."""
    return t * _IMAGENET_STD.to(t.device) + _IMAGENET_MEAN.to(t.device)


def _tensor_to_pil(t: torch.Tensor) -> Image.Image:
    """Convert a [0,1] CHW tensor to a PIL Image."""
    arr = (t.clamp(0, 1).cpu().numpy() * 255).astype(np.uint8)
    return Image.fromarray(arr.transpose(1, 2, 0))


# ---------------------------------------------------------------------------
# VAE Encoder loader (lazy singleton)
# ---------------------------------------------------------------------------
_vae_encoder = None


def _get_vae_encoder(device: torch.device) -> torch.nn.Module:
    """Load the Stable Diffusion VAE encoder (frozen)."""
    global _vae_encoder
    if _vae_encoder is not None:
        return _vae_encoder

    from diffusers import AutoencoderKL

    logger.info("Loading SD VAE encoder for Mist v2...")
    vae = AutoencoderKL.from_pretrained(
        "stabilityai/sd-vae-ft-mse",
        torch_dtype=torch.float32,
    )
    vae = vae.to(device).eval()
    for param in vae.parameters():
        param.requires_grad_(False)

    _vae_encoder = vae
    logger.info("VAE encoder loaded.")
    return _vae_encoder


# ---------------------------------------------------------------------------
# Core: PGD-based adversarial perturbation
# ---------------------------------------------------------------------------
def apply_mist_v2(
    image: Image.Image,
    *,
    epsilon: int = 8,
    steps: int = 3,
    device: torch.device | None = None,
) -> Image.Image:
    """Apply Mist v2 adversarial perturbation to *image*.

    Args:
        image: Input PIL Image (RGB).
        epsilon: Maximum perturbation magnitude in pixel space [0-255].
                 Default ``8`` as defined in MDD.
        steps: Number of PGD iterations. Default ``3`` (speed priority).
        device: Torch device. Falls back to CUDA if available.

    Returns:
        Protected PIL Image with adversarial noise applied.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    vae = _get_vae_encoder(device)

    # Ensure image dimensions are multiples of 8 (VAE requirement)
    w, h = image.size
    new_w = (w // 8) * 8
    new_h = (h // 8) * 8
    if (new_w, new_h) != (w, h):
        image = image.resize((new_w, new_h), Image.LANCZOS)

    # Prepare tensors
    x_orig = _to_tensor(image).unsqueeze(0).to(device)  # [1, 3, H, W] in [0,1]
    eps = epsilon / 255.0
    step_size = eps / max(steps, 1) * 1.5  # slightly larger than eps/steps

    # Compute target latent (clean encoding)
    with torch.no_grad():
        z_orig = vae.encode(_normalize(x_orig)).latent_dist.mean

    # Initialize adversarial image
    x_adv = x_orig.clone().detach()
    x_adv.requires_grad_(True)

    for i in range(steps):
        if x_adv.grad is not None:
            x_adv.grad.zero_()

        # Encode the adversarial image
        z_adv = vae.encode(_normalize(x_adv)).latent_dist.mean

        # Loss: maximize distance in latent space
        loss = -F.mse_loss(z_adv, z_orig)
        loss.backward()

        with torch.no_grad():
            # PGD step (gradient ascent to maximize loss = maximize latent distance)
            grad_sign = x_adv.grad.sign()
            x_adv = x_adv - step_size * grad_sign  # subtract because loss is negated

            # Project back into epsilon-ball around original
            perturbation = (x_adv - x_orig).clamp(-eps, eps)
            x_adv = (x_orig + perturbation).clamp(0.0, 1.0)

        x_adv = x_adv.detach().requires_grad_(True)

        logger.debug("Mist v2 step %d/%d — loss=%.6f", i + 1, steps, loss.item())

    # Convert back to PIL
    result = _tensor_to_pil(x_adv.squeeze(0).detach())

    # Restore original dimensions if resized
    if (new_w, new_h) != (w, h):
        result = result.resize((w, h), Image.LANCZOS)

    logger.info("Mist v2 applied (eps=%d, steps=%d)", epsilon, steps)
    return result
