# =============================================================================
# lore-anchor CPU Worker — Railway deployment
# Runs Mist v2 in freq mode (NumPy DCT), PixelSeal DWT, C2PA signing.
# No GPU required. Processing time: ~30-60s/image.
# =============================================================================
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=""
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install CPU-only PyTorch first (no CUDA overhead)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy CPU worker entrypoint
COPY main.py .

# Copy shared core modules from gpu-worker
# (Docker build context must be set to workers/ directory)
COPY ../gpu-worker/core ./core

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python3", "main.py"]
