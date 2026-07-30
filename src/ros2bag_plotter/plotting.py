from __future__ import annotations
from typing import Dict
import re
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

def build_combined_figure(topic_frames: Dict[str, pd.DataFrame]) -> go.Figure:
    topics = list(topic_frames.keys())
    fig = make_subplots(
        rows=max(1, len(topics)),
        cols=1,
        subplot_titles=topics,
        vertical_spacing=0.05
    )

    for r, topic in enumerate(topics, start=1):
        df = normalize_frame_for_contract(topic_frames[topic].copy())
        if TIME_COLUMN not in df.columns:
            continue

        x = pd.to_numeric(df[TIME_COLUMN], errors="coerce")
        ycols = _y_columns(df)

        for c in ycols:
            y = pd.to_numeric(df[c], errors="coerce")
            fig.add_trace(
                go.Scatter(x=x, y=y, mode="lines", name=f"{topic}:{c}"),
                row=r, col=1
            )

        fig.update_xaxes(title_text="time (s from bag start)", row=r, col=1)
        fig.update_yaxes(title_text="value", row=r, col=1)

    fig.update_layout(
        template="plotly_white",
        title="ROS2 signals vs normalized time",
        height=max(500, 330 * len(topics)),
        legend=dict(itemsizing="constant")
    )
    return fig

def build_per_topic_figure(topic: str, df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    df = normalize_frame_for_contract(df.copy())
    if TIME_COLUMN not in df.columns:
        return fig

    x = pd.to_numeric(df[TIME_COLUMN], errors="coerce")
    for c in _y_columns(df):
        y = pd.to_numeric(df[c], errors="coerce")
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=c))

    fig.update_layout(
        template="plotly_white",
        title=f"{topic} signals vs normalized time",
        xaxis_title="time (s from bag start)",
        yaxis_title="value"
    )
    return fig