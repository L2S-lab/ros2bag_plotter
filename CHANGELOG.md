# Changelog

All notable changes to this project will be documented in this file.

## v1.2.1 - 2026-08-05

### Changed
- Docker launcher now reuses existing images by default and rebuilds only when `REBUILD_IMAGE=1`.
- Docker one-liner launch command now uses `bash -c "$(curl -fsSL ...)"` for better Debian compatibility.
- Local launcher install target is now `~/.local/bin/ros2bag-plotter`, with startup update checks.
- In Docker runtime, checking **Open combined HTML after save** now shows a copyable host path instead of trying to auto-open the browser.
- Docker build now installs project code with `--no-build-isolation` and caches dependency installation in separate layers to avoid re-downloading packages on source-only rebuilds.
- Docker container entrypoint now runs `python3 -m ros2bag_plotter.main`, and the launcher rebuilds stale images automatically if runtime import checks fail.

## v1.2.0 - 2026-08-04

### Added
- Refresh button in the GUI to rescan bags in the currently selected root folder.
- Docker-based GUI runtime support with ROS distro selection and local-folder mounting.

### Changed
- Updated package/app version to `1.2.0`.

## v1.1.0 - 2026-07-31

### Added
- Per-topic derivative plotting via `Plot d1/d2` checkbox.
- First and second order derivative traces rendered in the same combined/per-topic figure HTML.
- Derivative support for array-channel fields (`*_channel_i`) per topic.
- Optional per-topic derivative smoothing via `Smooth d1/d2`.
- GUI control for smoothing window size (moving-average sample count).

### Changed
- Updated package/app version to `1.1.0`.
