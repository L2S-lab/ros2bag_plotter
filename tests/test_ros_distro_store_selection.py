from __future__ import annotations

from pathlib import Path

import pytest
from rosbags.typesys import Stores

from ros2bag_plotter.bag_reader import Ros2BagReader


@pytest.mark.parametrize(
    "distro",
    ["humble", "jazzy", "kilted", "lyrical", "rolling"],
)
def test_select_store_supports_requested_ros_distros(monkeypatch, distro):
    monkeypatch.setenv("ROS_DISTRO", distro)
    store = Ros2BagReader(Path("."))._select_store()
    assert isinstance(store, Stores)


def test_unknown_ros_distro_falls_back_to_latest(monkeypatch):
    monkeypatch.setenv("ROS_DISTRO", "unknown_future")
    store = Ros2BagReader(Path("."))._select_store()
    assert store == Stores.LATEST
