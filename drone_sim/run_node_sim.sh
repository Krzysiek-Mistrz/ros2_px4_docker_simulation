#!/usr/bin/env bash


set -euo pipefail

PX4_ROOT=$(pwd)/PX4-Autopilot
ROS_WS=$(pwd)/ws

export ROS_DOMAIN_ID=0

export AMENT_TRACE_SETUP_FILES=${AMENT_TRACE_SETUP_FILES:-}

set +u
source /opt/ros/humble/setup.bash
source "${ROS_WS}/install/setup.bash"
set -u

# START QGROUNDCONTROL!!!

echo "Starting microxrce (background)..."
( /home/px4/ros2/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent udp4 -p 8888 ) &
sleep 2

cd "${PX4_ROOT}"
echo "Starting px4..."
( make px4_sitl gz_x500 > /tmp/px4_sitl.log 2>&1 )
PX4_PID=$!
echo "PX4 PID=${PX4_PID}"
sleep 10

echo "Starting node..."
ros2 run dron_nav_pkg dron_nav_pkg
