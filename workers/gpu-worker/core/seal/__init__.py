# lore-anchor GPU Worker — PixelSeal module
# Lazy imports to avoid requiring torch for DWT-only usage.


def embed_watermark(*args, **kwargs):  # type: ignore[no-untyped-def]
    from core.seal.pixelseal import embed_watermark as _fn
    return _fn(*args, **kwargs)


def extract_watermark(*args, **kwargs):  # type: ignore[no-untyped-def]
    from core.seal.pixelseal import extract_watermark as _fn
    return _fn(*args, **kwargs)


def verify_watermark(*args, **kwargs):  # type: ignore[no-untyped-def]
    from core.seal.pixelseal import verify_watermark as _fn
    return _fn(*args, **kwargs)


__all__ = ["embed_watermark", "extract_watermark", "verify_watermark"]
