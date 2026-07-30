from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest
from rosbags.rosbag2 import Writer
from rosbags.typesys import Stores, get_types_from_msg, get_typestore

CUSTOM_MSG_TYPE = "my_pkg/msg/MyCustom"
CUSTOM_MSG_DEF = "float32 temperature\nfloat32[] values\n"


def _create_known_bag(path: Path) -> Path:
    store = get_typestore(Stores.ROS2_HUMBLE)
    types = store.types
    Time = types["builtin_interfaces/msg/Time"]
    Header = types["std_msgs/msg/Header"]
    Point = types["geometry_msgs/msg/Point"]
    Quaternion = types["geometry_msgs/msg/Quaternion"]
    Pose = types["geometry_msgs/msg/Pose"]
    PoseStamped = types["geometry_msgs/msg/PoseStamped"]
    Vector3 = types["geometry_msgs/msg/Vector3"]
    Twist = types["geometry_msgs/msg/Twist"]

    with Writer(path, version=8) as writer:
        pose_conn = writer.add_connection("/pose", "geometry_msgs/msg/PoseStamped", typestore=store)
        twist_conn = writer.add_connection("/twist", "geometry_msgs/msg/Twist", typestore=store)

        base_ts = 1_000_000_000
        for i in range(4):
            stamp = Time(sec=100 + i, nanosec=i * 1_000)
            header = Header(stamp=stamp, frame_id="map")
            pose = Pose(
                position=Point(x=float(i), y=float(i + 1), z=float(i + 2)),
                orientation=Quaternion(x=0.0, y=0.0, z=0.0, w=1.0),
            )
            pose_msg = PoseStamped(header=header, pose=pose)
            pose_raw = store.serialize_cdr(pose_msg, "geometry_msgs/msg/PoseStamped")

            twist_msg = Twist(
                linear=Vector3(x=float(i) * 0.1, y=float(i) * 0.2, z=float(i) * 0.3),
                angular=Vector3(x=float(i) * 0.4, y=float(i) * 0.5, z=float(i) * 0.6),
            )
            twist_raw = store.serialize_cdr(twist_msg, "geometry_msgs/msg/Twist")

            ts = base_ts + i * 100_000_000
            writer.write(pose_conn, ts, pose_raw)
            writer.write(twist_conn, ts + 1, twist_raw)
    return path


def _create_custom_bag(path: Path, *, include_schema_defs: bool) -> Path:
    store = get_typestore(Stores.ROS2_HUMBLE)
    store.register(get_types_from_msg(CUSTOM_MSG_DEF, CUSTOM_MSG_TYPE))
    msg_cls = store.types[CUSTOM_MSG_TYPE]

    with Writer(path, version=8) as writer:
        conn = writer.add_connection("/custom", CUSTOM_MSG_TYPE, typestore=store)
        base_ts = 2_000_000_000
        for i in range(3):
            msg = msg_cls(
                temperature=20.0 + i,
                values=np.array([1.0 + i, 2.0 + i, 3.0 + i], dtype=np.float32),
            )
            raw = store.serialize_cdr(msg, CUSTOM_MSG_TYPE)
            writer.write(conn, base_ts + i * 100_000_000, raw)

    if not include_schema_defs:
        db_file = next(path.glob("*.db3"))
        with sqlite3.connect(db_file) as con:
            con.execute("DELETE FROM message_definitions")
            con.commit()
    return path


@pytest.fixture()
def sample_bags(tmp_path: Path):
    known = _create_known_bag(tmp_path / "known_bag")
    custom = _create_custom_bag(tmp_path / "custom_bag", include_schema_defs=True)
    custom_missing_schema = _create_custom_bag(
        tmp_path / "custom_missing_schema_bag",
        include_schema_defs=False,
    )
    return {
        "known": known,
        "custom": custom,
        "custom_missing_schema": custom_missing_schema,
    }
