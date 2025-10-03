#!/bin/bash

# Setup X11 authentication
if [ ! -z "$XAUTHORITY" ] && [ -f "$XAUTHORITY" ]; then
    cp "$XAUTHORITY" /tmp/.docker.xauth 2>/dev/null || true
    chmod 644 /tmp/.docker.xauth 2>/dev/null || true
fi

# Create runtime directory
mkdir -p /tmp/runtime-root
chmod 700 /tmp/runtime-root

# Source ROS2 environment
if [ -f /opt/ros/humble/setup.bash ]; then
  source /opt/ros/humble/setup.bash
fi
if [ -f /home/px4/ros2_ws/install/setup.bash ]; then
  source /home/px4/ros2_ws/install/setup.bash || true
fi

# Test X11 connection (optional, for debugging)
if [ "$1" = "test-x11" ]; then
    echo "Testing X11 connection..."
    xauth list
    echo "DISPLAY: $DISPLAY"
    echo "Testing with xeyes..."
    timeout 5 xeyes || echo "X11 test failed or timed out"
    exit 0
fi

# bash ./build_px4.sh
# bash ./build_microxrce.sh

exec "$@"
