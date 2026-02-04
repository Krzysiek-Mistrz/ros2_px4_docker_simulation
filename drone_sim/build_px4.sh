#!/usr/bin/env bash


set -euo pipefail
echo "Cloning and building PX4 (v1.16.0)..."

if [ -d ./PX4-Autopilot ]; then
  rm -r ./PX4-Autopilot
fi

git clone --recursive -b v1.16.0 https://github.com/PX4/PX4-Autopilot.git ./PX4-Autopilot

cd ./PX4-Autopilot
bash ./Tools/setup/ubuntu.sh
echo "PX4 install done."

# 2 run:
# make px4_sitl gz_x500