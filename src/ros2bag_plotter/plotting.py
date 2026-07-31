from __future__ import annotations
from typing import Dict, Iterable
import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .export_contract import TIME_COLUMN, normalize_frame_for_contract

TIME_EXACT = {
    TIME_COLUMN, "time", "time_sec", "timestamp", "ts",
    "header.stamp.sec", "header.stamp.nanosec",
    "stamp.sec", "stamp.nanosec",
    "sec", "nanosec"
}

TIME_PATTERNS = [
    r"(^|\.|\_)time($|\.|\_)",
    r"(^|\.|\_)timestamp($|\.|\_)",
    r"(^|\.|\_)stamp($|\.|\_)",
    r"header\.stamp\.(sec|nanosec)$",
    r"\.stamp\.(sec|nanosec)$",
    r"(^|\.)(sec|nanosec)$",
]

def _is_time_like(col: str) -> bool:
    c = col.lower()
    if c in TIME_EXACT:
        return True
    return any(re.search(p, c) for p in TIME_PATTERNS)

def _y_columns(df: pd.DataFrame):
    cols = []
    for c in df.columns:
        if c == TIME_COLUMN:
            continue
        if _is_time_like(c):
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            cols.append(c)
    return cols

def _row_kind_title(topic: str, kind: str) -> str:
    if kind == "base":
        return topic
    if kind == "d1":
        return f"{topic} - first derivative"
    return f"{topic} - second derivative"

def _build_topic_row_specs(topics: list[str], derivative_topics: set[str]) -> list[tuple[str, str]]:
    specs: list[tuple[str, str]] = []
    for topic in topics:
        specs.append((topic, "base"))
        if topic in derivative_topics:
            specs.append((topic, "d1"))
            specs.append((topic, "d2"))
    return specs

def _plot_topic_base_traces(
    fig: go.Figure,
    row: int,
    topic: str,
    x: np.ndarray,
    df: pd.DataFrame,
    *,
    include_topic_prefix: bool,
):
    for c in _y_columns(df):
        y = pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float)
        trace_name = f"{topic}:{c}" if include_topic_prefix else c
        fig.add_trace(
            go.Scatter(x=x, y=y, mode="lines", name=trace_name),
            row=row,
            col=1,
        )

def _plot_topic_derivative_traces(
    fig: go.Figure,
    row: int,
    topic: str,
    x: np.ndarray,
    df: pd.DataFrame,
    order: int,
    *,
    include_topic_prefix: bool,
    smooth: bool = False,
    smooth_window: int = 5,
):
    suffix = "d1" if order == 1 else "d2"
    for c in _y_columns(df):
        y = pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float)
        d1, d2 = _first_second_derivative(x, y)
        dy = d1 if order == 1 else d2
        if smooth:
            dy = _smooth_derivative(dy, window=smooth_window)
        trace_name = f"{topic}:{c} {suffix}" if include_topic_prefix else f"{c} {suffix}"
        if smooth:
            trace_name = f"{trace_name} (smoothed)"
        if np.isfinite(dy).any():
            fig.add_trace(
                go.Scatter(x=x, y=dy, mode="lines", name=trace_name),
                row=row,
                col=1,
            )

def build_combined_figure(
    topic_frames: Dict[str, pd.DataFrame],
    derivative_topics: Iterable[str] | None = None,
    derivative_smoothing_topics: Iterable[str] | None = None,
    derivative_smoothing_window: int = 5,
) -> go.Figure:
    topics = list(topic_frames.keys())
    derivative_set = set(derivative_topics or [])
    smooth_set = set(derivative_smoothing_topics or [])
    row_specs = _build_topic_row_specs(topics, derivative_set)
    if not row_specs:
        row_specs = [("no_data", "base")]

    fig = make_subplots(
        rows=len(row_specs),
        cols=1,
        subplot_titles=[_row_kind_title(topic, kind) for topic, kind in row_specs],
        vertical_spacing=0.04,
    )

    for row, (topic, kind) in enumerate(row_specs, start=1):
        if topic not in topic_frames:
            continue
        df = normalize_frame_for_contract(topic_frames[topic].copy())
        if TIME_COLUMN not in df.columns:
            continue
        x = pd.to_numeric(df[TIME_COLUMN], errors="coerce").to_numpy(dtype=float)

        if kind == "base":
            _plot_topic_base_traces(fig, row, topic, x, df, include_topic_prefix=True)
            fig.update_yaxes(title_text="value", row=row, col=1)
        elif kind == "d1":
            _plot_topic_derivative_traces(
                fig,
                row,
                topic,
                x,
                df,
                order=1,
                include_topic_prefix=True,
                smooth=(topic in smooth_set),
                smooth_window=derivative_smoothing_window,
            )
            fig.update_yaxes(title_text="first derivative", row=row, col=1)
        else:
            _plot_topic_derivative_traces(
                fig,
                row,
                topic,
                x,
                df,
                order=2,
                include_topic_prefix=True,
                smooth=(topic in smooth_set),
                smooth_window=derivative_smoothing_window,
            )
            fig.update_yaxes(title_text="second derivative", row=row, col=1)

        fig.update_xaxes(title_text="time (s from bag start)", row=row, col=1)

    fig.update_layout(
        template="plotly_white",
        title="ROS2 signals vs normalized time",
        height=max(500, 280 * len(row_specs)),
        legend=dict(itemsizing="constant"),
    )
    return fig

def build_per_topic_figure(
    topic: str,
    df: pd.DataFrame,
    include_derivatives: bool = False,
    smooth_derivatives: bool = False,
    smooth_window: int = 5,
) -> go.Figure:
    df = normalize_frame_for_contract(df.copy())
    if TIME_COLUMN not in df.columns:
        return go.Figure()

    x = pd.to_numeric(df[TIME_COLUMN], errors="coerce").to_numpy(dtype=float)
    if not include_derivatives:
        fig = go.Figure()
        _plot_topic_base_traces(fig, 1, topic, x, df, include_topic_prefix=False)
        fig.update_layout(
            template="plotly_white",
            title=f"{topic} signals vs normalized time",
            xaxis_title="time (s from bag start)",
            yaxis_title="value",
        )
        return fig

    fig = make_subplots(
        rows=3,
        cols=1,
        subplot_titles=[
            topic,
            f"{topic} - first derivative",
            f"{topic} - second derivative",
        ],
        vertical_spacing=0.08,
    )
    _plot_topic_base_traces(fig, 1, topic, x, df, include_topic_prefix=False)
    _plot_topic_derivative_traces(
        fig,
        2,
        topic,
        x,
        df,
        order=1,
        include_topic_prefix=False,
        smooth=smooth_derivatives,
        smooth_window=smooth_window,
    )
    _plot_topic_derivative_traces(
        fig,
        3,
        topic,
        x,
        df,
        order=2,
        include_topic_prefix=False,
        smooth=smooth_derivatives,
        smooth_window=smooth_window,
    )
    fig.update_xaxes(title_text="time (s from bag start)", row=1, col=1)
    fig.update_xaxes(title_text="time (s from bag start)", row=2, col=1)
    fig.update_xaxes(title_text="time (s from bag start)", row=3, col=1)
    fig.update_yaxes(title_text="value", row=1, col=1)
    fig.update_yaxes(title_text="first derivative", row=2, col=1)
    fig.update_yaxes(title_text="second derivative", row=3, col=1)
    fig.update_layout(
        template="plotly_white",
        title=f"{topic} signals vs normalized time",
        height=980,
        legend=dict(itemsizing="constant"),
    )
    return fig

def _first_second_derivative(x: np.ndarray, y: np.ndarray):
    d1 = np.full_like(y, np.nan, dtype=float)
    d2 = np.full_like(y, np.nan, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 2:
        return d1, d2

    xv = x[mask]
    yv = y[mask]
    d1v = np.gradient(yv, xv)
    d1[mask] = d1v
    if mask.sum() >= 3:
        d2[mask] = np.gradient(d1v, xv)
    return d1, d2

def _smooth_derivative(values: np.ndarray, window: int = 5) -> np.ndarray:
    series = pd.Series(values, dtype=float)
    smooth = series.rolling(window=window, min_periods=1, center=True).mean()
    return smooth.to_numpy(dtype=float)

def build_topic_derivatives_figure(topic: str, df: pd.DataFrame) -> go.Figure:
    full = build_per_topic_figure(topic, df, include_derivatives=True)
    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=[f"{topic} - first derivative", f"{topic} - second derivative"],
        vertical_spacing=0.10,
    )
    for trace in full.data:
        name = str(trace.name or "")
        if " d1" in name:
            fig.add_trace(trace, row=1, col=1)
        elif " d2" in name:
            fig.add_trace(trace, row=2, col=1)
    fig.update_xaxes(title_text="time (s from bag start)", row=1, col=1)
    fig.update_xaxes(title_text="time (s from bag start)", row=2, col=1)
    fig.update_yaxes(title_text="first derivative", row=1, col=1)
    fig.update_yaxes(title_text="second derivative", row=2, col=1)
    fig.update_layout(
        template="plotly_white",
        title=f"{topic} first and second derivatives",
        height=760,
        legend=dict(itemsizing="constant"),
    )
    return fig