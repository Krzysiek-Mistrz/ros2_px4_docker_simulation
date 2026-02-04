#!/usr/bin/env bash


set -euo pipefail

WS_PATH=$(pwd)/ws
SRC_PATH="${WS_PATH}/src"

mkdir -p "$SRC_PATH"
cd "$SRC_PATH"

update_repo() {
    local repo_url=$1
    local repo_dir=$2
    if [ -d "$repo_dir" ]; then
        echo "Updating $repo_dir..."
        cd "$repo_dir" && git pull && cd ..
    else
        echo "Cloning $repo_dir..."
        git clone "$repo_url"
    fi
}

update_repo "https://github.com/PX4/px4_msgs.git" "px4_msgs"
update_repo "https://github.com/PX4/px4_ros_com.git" "px4_ros_com"

cd "$WS_PATH"

set +u
echo "Sourcing ROS 2 Humble..."
source /opt/ros/humble/setup.bash
set -u

echo "Building workspace..."
colcon build --symlink-install --packages-select px4_msgs
colcon build --symlink-install

set +u
source install/setup.bash
set -u

echo "Workspace ready!"