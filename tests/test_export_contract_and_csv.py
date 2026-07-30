from __future__ import annotations

import json

import pandas as pd

from ros2bag_plotter.export_contract import (
    TIME_COLUMN,
    export_contract_metadata,
    normalize_frame_for_contract,
)
from ros2bag_plotter.exporter import export_csv


def test_normalize_frame_renames_legacy_time_column():
    df = pd.DataFrame({"time_sec": [0.0, 1.0], "v": [2.0, 3.0]})
    out = normalize_frame_for_contract(df)
    assert list(out.columns)[0] == TIME_COLUMN
    assert TIME_COLUMN in out.columns
    assert "time_sec" not in out.columns


def test_export_csv_writes_contract_manifest_and_normalized_csv(tmp_path):
    bag_folder = tmp_path / "bag"
    frames = {"/topic": pd.DataFrame({"time_sec": [0.0, 1.0], "signal": [5.0, 6.0]})}
    export_csv(frames, bag_folder)

    csv_path = bag_folder / "csv" / "topic.csv"
    assert csv_path.exists()
    exported = pd.read_csv(csv_path)
    assert list(exported.columns)[0] == TIME_COLUMN
    assert "time_sec" not in exported.columns

    manifest_path = bag_folder / "csv" / "_export_contract.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["contract_version"] == export_contract_metadata()["contract_version"]
    assert manifest["time_column"] == TIME_COLUMN
