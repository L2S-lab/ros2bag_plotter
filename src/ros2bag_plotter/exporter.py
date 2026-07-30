from __future__ import annotations
from pathlib import Path
from typing import Dict
import json
import pandas as pd
import plotly.graph_objects as go
from .export_contract import export_contract_metadata, normalize_frame_for_contract, TIME_COLUMN
from .plotting import _y_columns

def ensure_dirs(bag_folder: Path):
    csv_dir = bag_folder / "csv"
    plot_dir = bag_folder / "plots"
    raw_dir = bag_folder / "raw_unknown"
    csv_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    return csv_dir, plot_dir, raw_dir

def safe_topic_name(topic: str) -> str:
    return topic.strip("/").replace("/", "__")

def write_export_contract_manifest(csv_dir: Path):
    manifest = csv_dir / "_export_contract.json"
    manifest.write_text(json.dumps(export_contract_metadata(), indent=2), encoding="utf-8")

def export_csv(topic_frames: Dict[str, pd.DataFrame], bag_folder: Path):
    csv_dir, _, _ = ensure_dirs(bag_folder)
    write_export_contract_manifest(csv_dir)
    for topic, df in topic_frames.items():
        out_df = normalize_frame_for_contract(df)
        if TIME_COLUMN in out_df.columns:
            out_df[TIME_COLUMN] = pd.to_numeric(out_df[TIME_COLUMN], errors="coerce")
        out_df.to_csv(csv_dir / f"{safe_topic_name(topic)}.csv", index=False)

def save_html(fig: go.Figure, bag_folder: Path, filename: str) -> Path:
    _, plot_dir, _ = ensure_dirs(bag_folder)
    out = plot_dir / filename
    stem = Path(filename).stem
    post_script = f"""
const gd = document.getElementById('{{plot_id}}');
if (gd) {{
  const controls = document.createElement('div');
  controls.style.display = 'flex';
  controls.style.gap = '8px';
  controls.style.margin = '0 0 10px 0';
  const btnPng = document.createElement('button');
  const btnSvg = document.createElement('button');
  btnPng.textContent = 'Save PNG';
  btnSvg.textContent = 'Save SVG';
  const baseName = {json.dumps(stem)};
  btnPng.onclick = () => Plotly.downloadImage(gd, {{format: 'png', filename: baseName, scale: 2}});
  btnSvg.onclick = () => Plotly.downloadImage(gd, {{format: 'svg', filename: baseName, scale: 1}});
  controls.appendChild(btnPng);
  controls.appendChild(btnSvg);
  gd.parentNode.insertBefore(controls, gd);
}}
"""
    fig.write_html(
        str(out),
        include_plotlyjs="cdn",
        config={
            "displaylogo": False,
            "toImageButtonOptions": {"format": "png", "filename": stem, "scale": 2},
        },
        post_script=post_script,
    )
    return out

def _save_image_matplotlib(
    topic_frames: Dict[str, pd.DataFrame],
    bag_folder: Path,
    filename_no_ext: str,
    ext: str,
) -> Path:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        raise RuntimeError(
            "PNG/SVG fallback requires matplotlib. Install it and retry."
        ) from exc

    _, plot_dir, _ = ensure_dirs(bag_folder)
    out = plot_dir / f"{filename_no_ext}.{ext}"
    topics = list(topic_frames.keys())
    rows = max(1, len(topics))
    fig_mpl, axes = plt.subplots(rows, 1, figsize=(14, max(4, 3.2 * rows)), squeeze=False)

    for idx, topic in enumerate(topics):
        ax = axes[idx][0]
        df = normalize_frame_for_contract(topic_frames[topic])
        if TIME_COLUMN not in df.columns:
            ax.set_title(f"{topic} (no {TIME_COLUMN})")
            ax.grid(True, alpha=0.25)
            continue

        x = pd.to_numeric(df[TIME_COLUMN], errors="coerce")
        ycols = _y_columns(df)
        plotted = 0
        for c in ycols:
            y = pd.to_numeric(df[c], errors="coerce")
            if y.notna().any():
                ax.plot(x, y, label=c, linewidth=1.0)
                plotted += 1

        ax.set_title(topic)
        ax.set_xlabel("time (s from bag start)")
        ax.set_ylabel("value")
        ax.grid(True, alpha=0.25)
        if plotted > 0:
            ax.legend(loc="upper right", fontsize=7, ncol=2)

    fig_mpl.tight_layout()
    if ext == "png":
        fig_mpl.savefig(out, format="png", dpi=180)
    else:
        fig_mpl.savefig(out, format=ext)
    plt.close(fig_mpl)
    return out

def save_image(
    fig: go.Figure,
    bag_folder: Path,
    filename_no_ext: str,
    ext: str,
    topic_frames: Dict[str, pd.DataFrame] | None = None,
) -> Path:
    _, plot_dir, _ = ensure_dirs(bag_folder)
    out = plot_dir / f"{filename_no_ext}.{ext}"
    try:
        fig.write_image(str(out))
    except Exception as exc:
        msg = str(exc)
        if "Kaleido requires Google Chrome to be installed" in msg:
            if topic_frames:
                return _save_image_matplotlib(topic_frames, bag_folder, filename_no_ext, ext)
            raise RuntimeError(
                "PNG/SVG export requires Chrome for Kaleido. "
                "Install Chrome, run: plotly_get_chrome, or provide topic frames for matplotlib fallback."
            ) from exc
        raise
    return out

def save_unknown_raw(bag_folder: Path, topic: str, ts_ns: int, raw_data: bytes):
    _, _, raw_dir = ensure_dirs(bag_folder)
    base = safe_topic_name(topic)
    out = raw_dir / f"{base}_{ts_ns}.cdr"
    out.write_bytes(raw_data)