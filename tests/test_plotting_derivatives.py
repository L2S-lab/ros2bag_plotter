from __future__ import annotations

import pandas as pd

from ros2bag_plotter.plotting import build_combined_figure, build_topic_derivatives_figure


def test_build_topic_derivatives_figure_has_first_and_second_order_traces():
    df = pd.DataFrame(
        {
            "t_sec": [0.0, 1.0, 2.0, 3.0, 4.0],
            "signal": [0.0, 1.0, 4.0, 9.0, 16.0],
        }
    )
    fig = build_topic_derivatives_figure("/demo", df)

    names = [t.name for t in fig.data]
    assert "signal d1" in names
    assert "signal d2" in names
    assert "first and second derivatives" in (fig.layout.title.text or "")


def test_build_topic_derivatives_figure_supports_array_channel_columns():
    df = pd.DataFrame(
        {
            "t_sec": [0.0, 1.0, 2.0, 3.0],
            "values_channel_0": [1.0, 2.0, 4.0, 8.0],
            "values_channel_1": [0.0, 1.0, 1.0, 2.0],
        }
    )
    fig = build_topic_derivatives_figure("/custom", df)
    names = [t.name for t in fig.data]
    assert "values_channel_0 d1" in names
    assert "values_channel_0 d2" in names
    assert "values_channel_1 d1" in names
    assert "values_channel_1 d2" in names


def test_build_combined_figure_includes_derivative_traces_in_same_figure():
    frames = {
        "/demo": pd.DataFrame(
            {
                "t_sec": [0.0, 1.0, 2.0, 3.0],
                "values_channel_0": [1.0, 2.0, 4.0, 8.0],
            }
        )
    }
    fig = build_combined_figure(frames, derivative_topics={"/demo"})
    names = [t.name for t in fig.data]
    assert "/demo:values_channel_0" in names
    assert "/demo:values_channel_0 d1" in names
    assert "/demo:values_channel_0 d2" in names


def test_build_combined_figure_supports_smoothed_derivative_traces():
    frames = {
        "/demo": pd.DataFrame(
            {
                "t_sec": [0.0, 1.0, 2.0, 3.0, 4.0],
                "signal": [0.0, 1.0, 4.0, 9.0, 16.0],
            }
        )
    }
    fig = build_combined_figure(
        frames,
        derivative_topics={"/demo"},
        derivative_smoothing_topics={"/demo"},
        derivative_smoothing_window=7,
    )
    names = [t.name for t in fig.data]
    assert "/demo:signal d1 (smoothed)" in names
    assert "/demo:signal d2 (smoothed)" in names
