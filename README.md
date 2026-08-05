# ROS2 Bag Plotter

python3 GUI tool to read ROS2 bag files, plot topic data, and export CSV/plots.

## Features

- Detects bag folders automatically (`metadata.yaml`, `.db3`, `.mcap`)
- Normalizes time to start at `0` seconds (`t_sec`)
- Plots known ROS message types directly
- Supports custom message recovery using pasted `.msg` definition
- Supports custom multi-field mapping (including array channels)
- Per-topic derivative checkbox (`Plot d1/d2`) to include first/second derivatives in the same plot figure/HTML
- Per-topic smoothing checkbox (`Smooth d1/d2`) for derivative traces, with GUI-selectable moving-average sample window
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

## Run with Docker (GUI + local folder access)

This project includes an interactive launcher that:

1. asks you to select ROS2 distro from the CI-supported list  
   (`humble`, `jazzy`, `kilted`, `lyrical`, `rolling`)
2. reuses an existing docker image for that distro (rebuild only when requested)
3. mounts your host root folder (default: `$HOME`) into the container
4. runs the GUI with X11 display forwarding
5. when installed as `~/.local/bin/ros2bag-plotter`, checks for launcher updates at startup
6. caches Python dependency installation in Docker layers so source-only rebuilds do not re-download all packages
7. automatically rebuilds stale cached images if runtime checks detect a broken install

### Prerequisites (Linux X11)

- Docker installed
- X11 session running (`DISPLAY` set)
- `xhost` available

### Launch

```bash
./scripts/run_gui_docker.sh
```

When prompted, enter:

- distro choice

Inside the container, your host root is mounted at `/host_root` and used as working directory. You can then pick any subfolder from the GUI root-folder picker. If `/media` or `/mnt` exist on host, they are mounted too.

In Docker runtime, when **Open combined HTML after save** is checked, the app does not try to auto-open a browser. It shows the full host path of the generated HTML and provides a **Copy path** button.

Optional: choose a different host root mount:

```bash
HOST_MOUNT_ROOT=/path/on/host ./scripts/run_gui_docker.sh
```

Force an image rebuild (for local Dockerfile/script changes):

```bash
REBUILD_IMAGE=1 ./scripts/run_gui_docker.sh
```

### Run Docker launcher directly from GitHub raw (no clone)

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/L2S-lab/ros2bag_plotter/main/scripts/run_gui_docker.sh)"
```

You can combine with custom host mount root:

```bash
HOST_MOUNT_ROOT=/path/on/host bash -c "$(curl -fsSL https://raw.githubusercontent.com/L2S-lab/ros2bag_plotter/main/scripts/run_gui_docker.sh)"
```

You can also force rebuild from the one-liner:

```bash
REBUILD_IMAGE=1 bash -c "$(curl -fsSL https://raw.githubusercontent.com/L2S-lab/ros2bag_plotter/main/scripts/run_gui_docker.sh)"
```

### Re-run later when using the curl method

Run the one-liner again:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/L2S-lab/ros2bag_plotter/main/scripts/run_gui_docker.sh)"
```

Or save a local launcher once (Debian-compatible, recommended):

```bash
mkdir -p "$HOME/.local/bin"
curl -fsSL https://raw.githubusercontent.com/L2S-lab/ros2bag_plotter/main/scripts/run_gui_docker.sh -o "$HOME/.local/bin/ros2bag-plotter"
chmod +x "$HOME/.local/bin/ros2bag-plotter"
grep -qxF 'export PATH="$HOME/.local/bin:$PATH"' "$HOME/.bashrc" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
grep -qxF 'alias ros2bag-plotter="$HOME/.local/bin/ros2bag-plotter"' "$HOME/.bashrc" || echo 'alias ros2bag-plotter="$HOME/.local/bin/ros2bag-plotter"' >> "$HOME/.bashrc"
source "$HOME/.bashrc"
ros2bag-plotter
```

After that, future runs are:

```bash
ros2bag-plotter
```

On each run, this local launcher checks for updates and can update itself in-place.
Disable the update check for a run with:

```bash
CHECK_FOR_UPDATES=0 ros2bag-plotter
```

### Docker base image and ROS distro mapping

To avoid Python/ROS version clashes, the container is built from a ROS base image (`ros:<distro>-ros-base`) instead of `python:slim`.

- `humble` -> `ros:humble-ros-base`
- `jazzy` -> `ros:jazzy-ros-base`
- `rolling` -> `ros:rolling-ros-base`
- `kilted` -> `ros:rolling-ros-base` (fallback)
- `lyrical` -> `ros:rolling-ros-base` (fallback)

The selected ROS distro is still passed as `ROS_DISTRO` in the container for runtime typestore selection.


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
python3 -m pip install --user --upgrade "git+https://github.com/L2S-lab/ros2bag_plotter.git@v1.2.0"
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
