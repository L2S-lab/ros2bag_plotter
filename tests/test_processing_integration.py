from __future__ import annotations

from pathlib import Path

import pytest

from ros2bag_plotter.processing_service import BagProcessingService
from ros2bag_plotter.schema_cache import SchemaCache
from ros2bag_plotter.type_mapping import TypeMappingStore
from tests.conftest import CUSTOM_MSG_DEF, CUSTOM_MSG_TYPE


def _service(tmp_path: Path) -> BagProcessingService:
    mapping_db = tmp_path / "mappings.db"
    schema_db = tmp_path / "schemas.db"
    return BagProcessingService(
        type_map_store=TypeMappingStore(db_path=mapping_db),
        schema_cache=SchemaCache(db_path=schema_db),
    )


def test_integration_known_topics(sample_bags, tmp_path):
    svc = _service(tmp_path)
    frames = svc.load_frames(sample_bags["known"], [])

    assert set(frames.keys()) == {"/pose", "/twist"}
    pose_df = frames["/pose"]
    assert pose_df["t_sec"].iloc[0] == pytest.approx(0.0)
    assert "value.pose.position.x" in pose_df.columns
    twist_df = frames["/twist"]
    assert "value.linear.x" in twist_df.columns


def test_integration_custom_topic_with_plugin_decoder(sample_bags, tmp_path):
    svc = _service(tmp_path)

    def plugin_decoder(topic: str, type_name: str, msg):
        if type_name != CUSTOM_MSG_TYPE:
            return None
        return {
            "topic_name_len": float(len(topic)),
            "temperature": float(msg.temperature),
            "first_value": float(msg.values[0]),
        }

    svc.register_custom_decoder("my-custom-plugin", plugin_decoder)
    frames = svc.load_frames(sample_bags["custom"], ["/custom"])
    assert "/custom" in frames
    df = frames["/custom"]
    assert "temperature" in df.columns
    assert "first_value" in df.columns
    assert df["t_sec"].iloc[0] == pytest.approx(0.0)


def test_integration_missing_schema_recovers_via_callback(sample_bags, tmp_path):
    svc = _service(tmp_path)
    schema_requests: list[tuple[str, str]] = []

    def schema_cb(type_name: str, err_text: str) -> str | None:
        schema_requests.append((type_name, err_text))
        return CUSTOM_MSG_DEF

    def mapping_cb(type_name: str, _msg):
        assert type_name == CUSTOM_MSG_TYPE
        return {
            "fields": [
                {"path": "values", "alias": "values", "mode": "array_channels"},
                {"path": "temperature", "alias": "temp", "mode": "scalar"},
            ]
        }

    frames = svc.load_frames(
        sample_bags["custom_missing_schema"],
        ["/custom"],
        request_schema_cb=schema_cb,
        request_mapping_cb=mapping_cb,
    )
    assert schema_requests
    assert "/custom" in frames
    df = frames["/custom"]
    assert "values_channel_0" in df.columns
    assert "temp" in df.columns
    assert len(df) == 3
