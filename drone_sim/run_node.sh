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

echo "Starting microxrce on /dev/ttyAMA0 (background)..."
( /home/px4/ros2/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent udp4 -p 8888 ) &
sudo pkill MicroXRCEAgent || true
sudo MicroXRCEAgent serial --dev /dev/ttyAMA0 -b 921600 &
AGENT_PID=$!
sleep 2

echo "Starting node..."
ros2 run dron_nav_pkg simple_flight_node

trap "kill $AGENT_PID" EXIT