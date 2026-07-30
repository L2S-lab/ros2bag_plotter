from __future__ import annotations
from typing import Any, Dict

PRIMITIVES = (int, float, bool, str, bytes)
INTERNAL_KEYS = {"__msgtype__"}

def _as_sequence(v: Any):
    if isinstance(v, (list, tuple)):
        return list(v)
    if hasattr(v, "tolist"):
        try:
            arr = v.tolist()
            if isinstance(arr, list):
                return arr
        except Exception:
            return None
    if hasattr(v, "__iter__") and not isinstance(v, (str, bytes, dict)):
        try:
            return list(v)
        except Exception:
            return None
    return None


def flatten_ros_message(msg: Any, prefix: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if hasattr(msg, "get_fields_and_field_types"):
        for f in msg.get_fields_and_field_types().keys():
            v = getattr(msg, f)
            k = f"{prefix}.{f}" if prefix else f
            _flatten(v, k, out)
    else:
        _flatten(msg, prefix or "value", out)
    return out


def _flatten(v: Any, k: str, out: Dict[str, Any]):
    if isinstance(v, PRIMITIVES):
        out[k] = v
    elif isinstance(v, dict):
        for dk, dv in v.items():
            if str(dk) in INTERNAL_KEYS:
                continue
            _flatten(dv, f"{k}.{dk}" if k else str(dk), out)
    else:
        seq = _as_sequence(v)
        if seq is not None:
            if len(seq) == 0:
                out[k] = None
            else:
                for i, x in enumerate(seq):
                    if isinstance(x, PRIMITIVES):
                        out[f"{k}[{i}]"] = x
                    else:
                        _flatten(x, f"{k}[{i}]", out)
        elif hasattr(v, "__dict__"):
            for fk, fv in vars(v).items():
                if fk in INTERNAL_KEYS:
                    continue
                child_key = f"{k}.{fk}" if k else fk
                _flatten(fv, child_key, out)
        elif hasattr(v, "get_fields_and_field_types"):
            out.update(flatten_ros_message(v, k))
        else:
            out[k] = str(v)