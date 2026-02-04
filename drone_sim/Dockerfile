FROM osrf/ros:humble-desktop-jammy

SHELL ["/bin/bash", "-c"]
USER root

# Create px4 user with sudo privileges
RUN useradd -m -s /bin/bash px4 && \
    echo "px4:px4" | chpasswd && \
    usermod -aG sudo px4 && \
    usermod -aG dialout px4 && \
    echo "px4 ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

WORKDIR /home/px4/ros2_ws

# avoid interactive prompts
ARG DEBIAN_FRONTEND=noninteractive
ENV DEBIAN_FRONTEND=${DEBIAN_FRONTEND}

# ensure add-apt-repository is available, enable universe, then install packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends software-properties-common && \
    add-apt-repository universe && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git wget unzip python3-pip \
    libasio-dev libtinyxml2-dev libbullet-dev libssl-dev pkg-config \
    python3-colcon-common-extensions \
    python3-flake8 \
    python3-pytest-cov \
    python3-rosdep \
    python3-setuptools \
    python3-vcstool \
    python3-colcon-clean \
    python3-jinja2 \
    python3-empy \
    python3-toml \
    python3-numpy \
    python3-yaml \
    python3-dev \
    clang-format \
    ros-humble-ament-cmake \
    ros-humble-ament-cmake-auto \
    ros-humble-ament-lint-auto \
    ros-humble-ament-lint-cmake \
    ros-humble-ros-base \
    ros-dev-tools \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    protobuf-compiler \
    nano \
    locales \
    sudo \
    libgazebo-dev libeigen3-dev libopencv-dev \
    libxslt-dev libxml2-dev \
    mesa-utils libgl1 libgl1-mesa-glx libglu1-mesa libgl1-mesa-dri \
    libvulkan1 vulkan-tools \
    x11-apps xauth \
    libegl1-mesa libgles2-mesa \
    libglx-mesa0 libglapi-mesa \
    fuse libfuse2 \
    libxcb-xinerama0 libxkbcommon-x11-0 libxcb-cursor-dev libxcb-cursor0 -y \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
        apt-get install -y --no-install-recommends \
        pulseaudio \
        alsa-utils \
        pipewire \
        pipewire-pulse \
        libpipewire-0.3-0 \
        libpipewire-0.3-dev \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-ugly \
        gstreamer1.0-libav \
        gstreamer1.0-tools \
        libgstreamer1.0-0 \
        libgstreamer-plugins-base1.0-0 \
        speech-dispatcher \
        espeak \
        espeak-data \
        libspeechd-dev \
        qtspeech5-speechd-plugin

RUN wget https://d176tv9ibo4jno.cloudfront.net/latest/QGroundControl-x86_64.AppImage

RUN locale-gen en_US.UTF-8 && \
    update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8

# ROS 2 Humble + colcon (some packages may already be installed above,
# but keeping this for idempotency)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ros-humble-desktop \
      ros-humble-rmw-fastrtps-cpp \
      python3-colcon-common-extensions \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    kconfiglib \
    jinja2 \
    empy==3.3.4 \
    jsonschema \
    pyros-genmsg \
    setuptools==58.2.0
    
# Gazebo/rviz nvidia
ENV QT_X11_NO_MITSHM=1
ENV DISPLAY=:1

# Copy QGroundControl from host machine
RUN chmod +x ./QGroundControl-x86_64.AppImage && \
    ln -s ./QGroundControl-x86_64.AppImage /usr/local/bin/qgroundcontrol

RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc && \
    echo "source /home/px4/ros2_ws/install/setup.bash" >> /root/.bashrc && \
    echo "source /opt/ros/humble/setup.bash" >> /home/px4/.bashrc && \
    echo "source /home/px4/ros2_ws/install/setup.bash" >> /home/px4/.bashrc && \
    chown -R px4:px4 /home/px4

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]


