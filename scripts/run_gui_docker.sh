#!/usr/bin/env bash
set -euo pipefail

DISTROS=("humble" "jazzy" "kilted" "lyrical" "rolling")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd || true)"
DEFAULT_REMOTE_CONTEXT="https://github.com/L2S-lab/ros2bag_plotter.git#main"
REMOTE_SCRIPT_URL="https://raw.githubusercontent.com/L2S-lab/ros2bag_plotter/main/scripts/run_gui_docker.sh"
LOCAL_LAUNCHER_PATH="${HOME}/.local/bin/ros2bag-plotter"

check_for_launcher_updates() {
  if [[ "${CHECK_FOR_UPDATES:-1}" != "1" ]]; then
    return
  fi
  if [[ -z "${BASH_SOURCE[0]:-}" || ! -f "${BASH_SOURCE[0]}" ]]; then
    return
  fi

  local current_script
  current_script="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)/$(basename "${BASH_SOURCE[0]}")"
  if [[ "${current_script}" != "${LOCAL_LAUNCHER_PATH}" ]]; then
    return
  fi
  if ! command -v curl >/dev/null 2>&1; then
    return
  fi

  local remote_file
  remote_file="$(mktemp)"
  if ! curl -fsSL "${REMOTE_SCRIPT_URL}" -o "${remote_file}"; then
    rm -f "${remote_file}"
    return
  fi
  if cmp -s "${current_script}" "${remote_file}"; then
    rm -f "${remote_file}"
    return
  fi

  echo "A launcher update is available."
  read -r -p "Update ${LOCAL_LAUNCHER_PATH} now? [Y/n]: " update_choice
  update_choice="${update_choice:-Y}"
  if [[ "${update_choice}" =~ ^[Yy]$ ]]; then
    cp "${remote_file}" "${current_script}"
    chmod +x "${current_script}"
    rm -f "${remote_file}"
    echo "Launcher updated. Restarting..."
    exec "${current_script}" "$@"
  fi
  rm -f "${remote_file}"
}

check_for_launcher_updates "$@"

echo "Select ROS2 distro for container build/install:"
for i in "${!DISTROS[@]}"; do
  printf "  %d) %s\n" "$((i + 1))" "${DISTROS[$i]}"
done

read -r -p "Enter choice [1-${#DISTROS[@]}] (default 1): " choice
choice="${choice:-1}"
if ! [[ "$choice" =~ ^[0-9]+$ ]] || (( choice < 1 || choice > ${#DISTROS[@]} )); then
  echo "Invalid selection."
  exit 1
fi
ROS_DISTRO_SELECTED="${DISTROS[$((choice - 1))]}"

case "${ROS_DISTRO_SELECTED}" in
  humble|jazzy|rolling)
    ROS_IMAGE_DISTRO="${ROS_DISTRO_SELECTED}"
    ;;
  kilted|lyrical)
    ROS_IMAGE_DISTRO="rolling"
    ;;
  *)
    ROS_IMAGE_DISTRO="rolling"
    ;;
esac

HOST_MOUNT_ROOT="${HOST_MOUNT_ROOT:-$HOME}"
HOST_MOUNT_ROOT="$(cd "$HOST_MOUNT_ROOT" && pwd)"

if [[ ! -d "$HOST_MOUNT_ROOT" ]]; then
  echo "Folder does not exist: $HOST_MOUNT_ROOT"
  exit 1
fi

if [[ -z "${DISPLAY:-}" ]]; then
  echo "DISPLAY is not set. Start an X11 session first."
  exit 1
fi

if [[ -n "${DOCKER_BUILD_CONTEXT:-}" ]]; then
  DOCKER_CONTEXT="${DOCKER_BUILD_CONTEXT}"
elif [[ -n "${SCRIPT_DIR}" && -f "${SCRIPT_DIR}/../Dockerfile" ]]; then
  DOCKER_CONTEXT="$(cd "${SCRIPT_DIR}/.." && pwd)"
else
  DOCKER_CONTEXT="${DEFAULT_REMOTE_CONTEXT}"
fi

IMAGE_TAG="ros2bag-plotter:${ROS_DISTRO_SELECTED}"
if docker image inspect "${IMAGE_TAG}" >/dev/null 2>&1 && [[ "${REBUILD_IMAGE:-0}" != "1" ]]; then
  if docker run --rm --entrypoint python3 "${IMAGE_TAG}" -c "import ros2bag_plotter" >/dev/null 2>&1; then
    echo "Using existing image: ${IMAGE_TAG} (set REBUILD_IMAGE=1 to rebuild)."
  else
    echo "Existing image is missing ros2bag_plotter runtime. Rebuilding image."
    REBUILD_IMAGE=1
  fi
fi

if [[ "${REBUILD_IMAGE:-0}" == "1" ]]; then
  echo "REBUILD_IMAGE=1 set; rebuilding image: ${IMAGE_TAG}"
  if [[ "${ROS_IMAGE_DISTRO}" != "${ROS_DISTRO_SELECTED}" ]]; then
    echo "Note: using base image ros:${ROS_IMAGE_DISTRO}-ros-base for selected distro ${ROS_DISTRO_SELECTED}."
  fi
  echo "Build context: ${DOCKER_CONTEXT}"
  docker build \
    --build-arg ROS_IMAGE_DISTRO="${ROS_IMAGE_DISTRO}" \
    --build-arg APP_ROS_DISTRO="${ROS_DISTRO_SELECTED}" \
    -t "${IMAGE_TAG}" \
    "${DOCKER_CONTEXT}"
else
  if ! docker image inspect "${IMAGE_TAG}" >/dev/null 2>&1; then
    echo "Building image: ${IMAGE_TAG}"
    if [[ "${ROS_IMAGE_DISTRO}" != "${ROS_DISTRO_SELECTED}" ]]; then
      echo "Note: using base image ros:${ROS_IMAGE_DISTRO}-ros-base for selected distro ${ROS_DISTRO_SELECTED}."
    fi
    echo "Build context: ${DOCKER_CONTEXT}"
    docker build \
      --build-arg ROS_IMAGE_DISTRO="${ROS_IMAGE_DISTRO}" \
      --build-arg APP_ROS_DISTRO="${ROS_DISTRO_SELECTED}" \
      -t "${IMAGE_TAG}" \
      "${DOCKER_CONTEXT}"
  fi
fi

echo "Allowing local docker GUI access via X11..."
xhost +local:docker >/dev/null
cleanup() {
  xhost -local:docker >/dev/null || true
}
trap cleanup EXIT

echo "Running GUI with mounted host root: ${HOST_MOUNT_ROOT}"
docker_args=(
  --rm -it
  -e DISPLAY
  -e ROS_DISTRO="${ROS_DISTRO_SELECTED}"
  -e HOST_MOUNT_ROOT="${HOST_MOUNT_ROOT}"
  -e HOST_MOUNT_POINT="/host_root"
  -e QT_X11_NO_MITSHM=1
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw
  -v "${HOST_MOUNT_ROOT}:/host_root:rw"
  -w /host_root
)

if [[ -d /media ]]; then
  docker_args+=(-v /media:/media:rw)
fi
if [[ -d /mnt ]]; then
  docker_args+=(-v /mnt:/mnt:rw)
fi

docker run "${docker_args[@]}" "${IMAGE_TAG}"
