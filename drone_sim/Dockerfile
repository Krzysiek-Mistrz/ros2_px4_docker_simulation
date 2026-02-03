FROM ros:humble-ros-base-jammy

SHELL ["/bin/bash", "-c"]
USER root

# 1. Użytkownik i uprawnienia
RUN useradd -m -s /bin/bash px4 && \
    echo "px4:px4" | chpasswd && \
    usermod -aG sudo px4 && \
    usermod -aG dialout px4 && \
    echo "px4 ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

WORKDIR /home/px4/ros2_ws

# Unikanie interaktywnych promptów
ARG DEBIAN_FRONTEND=noninteractive
ENV DEBIAN_FRONTEND=${DEBIAN_FRONTEND}

# 2. Instalacja podstawowych narzędzi i ROS 2 Base
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    wget \
    unzip \
    python3-pip \
    python3-rosdep \
    python3-colcon-common-extensions \
    python3-vcstool \
    libasio-dev \
    libtinyxml2-dev \
    libeigen3-dev \
    libopencv-dev \
    nano \
    locales \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# 4. Pakiety Pythonowe potrzebne do PX4 i skryptów autonomii
RUN pip3 install --no-cache-dir \
    pyros-genmsg \
    setuptools==58.2.0 \
    kconfiglib \
    jinja2 \
    empy==3.3.4 \
    jsonschema \
    pyros-genmsg \
    numpy \
    toml \
    pyyaml

# 5. Konfiguracja Locales
RUN locale-gen en_US.UTF-8 && \
    update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8

# 6. Pakiety ROS2 niezbędne do lotu (bez Desktop/GUI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-humble-ros-base \
    ros-humble-nav2-msgs \
    ros-humble-geographic-msgs \
    ros-humble-sensor-msgs \
    ros-humble-geometry-msgs \
    && rm -rf /var/lib/apt/lists/*

# Konfiguracja środowiska
RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc && \
    echo "source /home/px4/ros2_ws/install/setup.bash" >> /root/.bashrc && \
    echo "source /opt/ros/humble/setup.bash" >> /home/px4/.bashrc && \
    chown -R px4:px4 /home/px4

# Jeśli masz swój entrypoint.sh, upewnij się, że jest w tym samym folderze
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER px4
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
