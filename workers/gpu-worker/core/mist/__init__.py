# lore-anchor GPU Worker — Mist v2 module
from core.mist.mist_v2 import MistMode


def apply_mist_v2(*args, **kwargs):  # type: ignore[no-untyped-def]
    from core.mist.mist_v2 import apply_mist_v2 as _fn
    return _fn(*args, **kwargs)


__all__ = ["apply_mist_v2", "MistMode"]
