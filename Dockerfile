ARG ROS_IMAGE_DISTRO=humble
FROM ros:${ROS_IMAGE_DISTRO}-ros-base

ARG APP_ROS_DISTRO=humble
ENV ROS_DISTRO=${APP_ROS_DISTRO}
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV QT_X11_NO_MITSHM=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
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
COPY . /app
RUN python3 -m pip install --upgrade pip && python3 -m pip install .

ENTRYPOINT ["ros2bag-plotter"]
