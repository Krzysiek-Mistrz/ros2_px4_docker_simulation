#!/usr/bin/env bash


set -euo pipefail

echo "Cloning and building Micro-XRCE-DDS-Agent..."
if [ ! -d ./Micro-XRCE-DDS-Agent ]; then
  rm -r ./Micro-XRCE-DDS-Agent
fi

git clone -b v3.0.1 https://github.com/eProsima/Micro-XRCE-DDS-Agent.git ./Micro-XRCE-DDS-Agent

cd ./Micro-XRCE-DDS-Agent
mkdir -p build && cd build
cmake ..
make
sudo make install
sudo ldconfig

echo "Micro XRCE install done. Binary: ./Micro-XRCE-DDS-Agent/build/MicroXRCEAgent"
