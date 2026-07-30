from __future__ import annotations

import numpy as np

from ros2bag_plotter.msg_flatten import flatten_ros_message


class _Inner:
    def __init__(self):
        self.values = np.array([1.5, 2.5], dtype=np.float32)
        self.flag = True
        self.__msgtype__ = "pkg/msg/Inner"


class _Outer:
    def __init__(self):
        self.inner = _Inner()
        self.name = "ok"
        self.__msgtype__ = "pkg/msg/Outer"


def test_flatten_handles_object_tree_and_array_channels():
    out = flatten_ros_message(_Outer())
    assert out["value.inner.values[0]"] == 1.5
    assert out["value.inner.values[1]"] == 2.5
    assert out["value.inner.flag"] is True
    assert out["value.name"] == "ok"
    assert not any("__msgtype__" in key for key in out.keys())


def test_flatten_handles_nested_dict_payload():
    payload = {"a": {"b": [1, 2, 3]}, "__msgtype__": "ignored"}
    out = flatten_ros_message(payload)
    assert out["value.a.b[0]"] == 1
    assert out["value.a.b[2]"] == 3
