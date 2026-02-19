# =============================================================================
# lore-anchor GPU Worker
# Base: NVIDIA CUDA 12.1 Runtime on Ubuntu 22.04
# Optimized: ~1.5 GB smaller via stripping test data & build artifacts
# =============================================================================
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# --- System dependencies ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- Working directory ---
WORKDIR /app

# --- Python dependencies (with post-install cleanup to shrink image) ---
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt \
    && find /usr/local/lib/python3.10/dist-packages -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.10/dist-packages -type d -name "test" -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.10/dist-packages -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true \
    && rm -rf /usr/local/lib/python3.10/dist-packages/torch/test \
    && rm -rf /usr/local/lib/python3.10/dist-packages/torch/testing/_internal \
    && rm -rf /usr/local/lib/python3.10/dist-packages/caffe2 \
    && find /usr/local/lib/python3.10/dist-packages/torch -name "*.a" -delete 2>/dev/null || true \
    && find /usr/local/lib/python3.10/dist-packages -name "*.pyc" -delete 2>/dev/null || true

# --- Application code ---
COPY . .

# --- Entrypoint ---
CMD ["python3", "main.py"]
