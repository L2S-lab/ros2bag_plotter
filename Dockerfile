ARG ROS_IMAGE_DISTRO=humble
FROM ros:${ROS_IMAGE_DISTRO}-ros-base

ARG APP_ROS_DISTRO=humble
ENV ROS_DISTRO=${APP_ROS_DISTRO}
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV QT_X11_NO_MITSHM=1
ENV PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    x11-xserver-utils \
    xdg-utils \
    libegl1 \
    libgl1 \
    libopengl0 \
    libglib2.0-0 \
    libx11-xcb1 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install runtime dependencies in a separate layer so source-only changes
# do not force dependency redownload.
COPY requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src

ENTRYPOINT ["python3", "-m", "ros2bag_plotter.main"]
