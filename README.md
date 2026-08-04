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
2. builds a docker image with that distro argument
3. mounts your host root folder (default: `$HOME`) into the container
4. runs the GUI with X11 display forwarding

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

Optional: choose a different host root mount:

```bash
HOST_MOUNT_ROOT=/path/on/host ./scripts/run_gui_docker.sh
```

### Run Docker launcher directly from GitHub raw (no clone)

```bash
curl -fsSL https://raw.githubusercontent.com/L2S-lab/ros2bag_plotter/main/scripts/run_gui_docker.sh | bash
```

You can combine with custom host mount root:

```bash
curl -fsSL https://raw.githubusercontent.com/L2S-lab/ros2bag_plotter/main/scripts/run_gui_docker.sh | HOST_MOUNT_ROOT=/path/on/host bash
```

### Re-run later when using the curl method

Run the one-liner again:

```bash
curl -fsSL https://raw.githubusercontent.com/L2S-lab/ros2bag_plotter/main/scripts/run_gui_docker.sh | bash
```

Or save a local launcher once (recommended):

```bash
mkdir -p ~/.local/bin
curl -fsSL https://raw.githubusercontent.com/L2S-lab/ros2bag_plotter/main/scripts/run_gui_docker.sh -o ~/.local/bin/ros2bag-plotter-docker
chmod +x ~/.local/bin/ros2bag-plotter-docker
~/.local/bin/ros2bag-plotter-docker
```

After that, future runs are:

```bash
~/.local/bin/ros2bag-plotter-docker
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
