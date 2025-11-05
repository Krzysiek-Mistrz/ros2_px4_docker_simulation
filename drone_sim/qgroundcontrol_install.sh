#!/bin/bash

# QGroundControl Installation Script
set -e

echo "Installing QGroundControl dependencies..."

# Add user to dialout group (will require logout/login to take effect)
sudo usermod -a -G dialout $USER

# Remove modemmanager
sudo apt-get update
sudo apt-get remove modemmanager -y

# Install dependencies
sudo apt-get install -y \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-libav \
    gstreamer1.0-gl \
    libfuse2 \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    libxcb-cursor-dev

# Download QGroundControl AppImage
echo "Downloading QGroundControl..."
wget https://d176tv9ibo4jno.cloudfront.net/latest/QGroundControl-x86_64.AppImage -O QGroundControl-x86_64.AppImage

# Make it executable
chmod +x ./QGroundControl-x86_64.AppImage

echo "Installation completed!"
echo "Note: You may need to logout and login again for the dialout group changes to take effect."
echo "Run QGroundControl with: ./QGroundControl-x86_64.AppImage"