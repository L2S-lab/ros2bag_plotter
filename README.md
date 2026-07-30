# ROS2 Bag Plotter

python3 GUI tool to read ROS2 bag files, plot topic data, and export CSV/plots.

## Features

- Detects bag folders automatically (`metadata.yaml`, `.db3`, `.mcap`)
- Normalizes time to start at `0` seconds (`t_sec`)
- Plots known ROS message types directly
- Supports custom message recovery using pasted `.msg` definition
- Supports custom multi-field mapping (including array channels)
- Exports:
  - CSV files to `csv/`
  - HTML plots to `plots/`
  - PNG/SVG plots to `plots/` (Plotly or Matplotlib fallback)

## Installation

```bash
git clone https://github.com/L2S-lab/ros2bag_plotter.git
cd ros2bag_plotter
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Install directly from GitHub (no clone)

```bash
python3 -m pip install --user "git+https://github.com/L2S-lab/ros2bag_plotter.git@main"
```

For development tools:

```bash
git clone https://github.com/L2S-lab/ros2bag_plotter.git
cd ros2bag_plotter
python3 -m venv .venv
pip install -e .[dev]
```

## Run

```bash
ros2bag-plotter
```

In the app:

1. Select root folder containing one or more bag folders.
2. Pick bag and topics.
3. Plot, export CSV, or batch export all bags.


### Check and update later (pip + GitHub)

Check installed version:

```bash
python3 -m pip show ros2bag-plotter
```

Update to latest `main`:

```bash
python3 -m pip install --user --upgrade "git+https://github.com/L2S-lab/ros2bag_plotter.git@main"
```

Install/update to specific tag or commit:

```bash
python3 -m pip install --user --upgrade "git+https://github.com/L2S-lab/ros2bag_plotter.git@v1.0.0"
python3 -m pip install --user --upgrade "git+https://github.com/L2S-lab/ros2bag_plotter.git@<commit_sha>"
```

Force reinstall from GitHub even if version string is unchanged:

```bash
python3 -m pip install --user --upgrade --force-reinstall "git+https://github.com/L2S-lab/ros2bag_plotter.git@main"
```


## Testing

```bash
ruff check src tests --select F,E9
pytest -q
```
