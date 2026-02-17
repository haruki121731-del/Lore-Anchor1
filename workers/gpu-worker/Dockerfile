# =============================================================================
# lore-anchor GPU Worker
# Base: NVIDIA CUDA 12.1 Runtime on Ubuntu 22.04
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

# --- Python dependencies ---
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# --- Application code ---
COPY . .

# --- Entrypoint ---
CMD ["python3", "main.py"]
