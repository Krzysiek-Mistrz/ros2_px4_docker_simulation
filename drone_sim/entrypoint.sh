#!/bin/bash
if [ -f /opt/ros/humble/setup.bash ]; then
  source /opt/ros/humble/setup.bash
fi
if [ -f /home/px4/ros2_ws/install/setup.bash ]; then
  source /home/px4/ros2_ws/install/setup.bash || true
fi

# bash ./build_px4.sh
# bash ./build_microxrce.sh

exec "$@"
