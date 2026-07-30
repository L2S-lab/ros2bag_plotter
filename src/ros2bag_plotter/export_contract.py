from __future__ import annotations

from typing import Any, Dict

import pandas as pd

EXPORT_CONTRACT_VERSION = 1
TIME_COLUMN = "t_sec"
TIME_NORMALIZATION = "seconds_from_first_selected_message"
CHANNEL_INDEX_BASE = 0
CHANNEL_TEMPLATE = "{base}_channel_{index}"
LEGACY_TIME_COLUMNS = ("time_sec", "time")


def make_channel_name(base: str, index: int) -> str:
    return CHANNEL_TEMPLATE.format(base=base, index=int(index))


def normalize_record_for_contract(record: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(record)
    if TIME_COLUMN not in out:
        for legacy in LEGACY_TIME_COLUMNS:
            if legacy in out:
                out[TIME_COLUMN] = out.pop(legacy)
                break
    return out


def normalize_frame_for_contract(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if TIME_COLUMN not in out.columns:
        for legacy in LEGACY_TIME_COLUMNS:
            if legacy in out.columns:
                out = out.rename(columns={legacy: TIME_COLUMN})
                break
    if TIME_COLUMN in out.columns:
        cols = [TIME_COLUMN] + [c for c in out.columns if c != TIME_COLUMN]
        out = out[cols]
    return out


def export_contract_metadata() -> Dict[str, Any]:
    return {
        "contract_version": EXPORT_CONTRACT_VERSION,
        "time_column": TIME_COLUMN,
        "time_normalization": TIME_NORMALIZATION,
        "channel_index_base": CHANNEL_INDEX_BASE,
        "channel_naming": CHANNEL_TEMPLATE,
        "legacy_time_columns_supported": list(LEGACY_TIME_COLUMNS),
    }
