#!/bin/bash

# Setup X11 authentication
if [ ! -z "$XAUTHORITY" ] && [ -f "$XAUTHORITY" ]; then
    cp "$XAUTHORITY" /tmp/.docker.xauth 2>/dev/null || true
    chmod 644 /tmp/.docker.xauth 2>/dev/null || true
else
    # Create xauth file if it doesn't exist
    touch /tmp/.docker.xauth
    chmod 644 /tmp/.docker.xauth
    # Try to merge existing X authority
    if [ ! -z "$DISPLAY" ]; then
        xauth nlist $DISPLAY 2>/dev/null | sed -e 's/^..../ffff/' | xauth -f /tmp/.docker.xauth nmerge - 2>/dev/null || true
    fi
fi

# Set XAUTHORITY for all users
export XAUTHORITY=/tmp/.docker.xauth

# Create runtime directory
mkdir -p /tmp/runtime-root
chmod 700 /tmp/runtime-root

# Fix ownership of /home/px4/ros2 if mounted
if [ -d /home/px4/ros2 ]; then
    chown -R px4:px4 /home/px4/ros2 2>/dev/null || true
fi

# Fix USB device permissions for Pixhawk
# Add px4 user to the groups that own USB devices
for device in /dev/ttyACM* /dev/ttyUSB*; do
    if [ -e "$device" ]; then
        # Get the group ID of the device
        DEVICE_GID=$(stat -c '%g' "$device" 2>/dev/null)
        if [ ! -z "$DEVICE_GID" ]; then
            # Get the group name (if it exists)
            DEVICE_GROUP=$(getent group "$DEVICE_GID" | cut -d: -f1)
            if [ ! -z "$DEVICE_GROUP" ]; then
                echo "Adding px4 user to group $DEVICE_GROUP (GID: $DEVICE_GID) for $device"
                usermod -aG "$DEVICE_GROUP" px4 2>/dev/null || true
            else
                # Group doesn't exist, create it
                echo "Creating group with GID $DEVICE_GID for $device"
                groupadd -g "$DEVICE_GID" "device_$DEVICE_GID" 2>/dev/null || true
                usermod -aG "device_$DEVICE_GID" px4 2>/dev/null || true
            fi
            # Also set permissions to be more permissive
            chmod 666 "$device" 2>/dev/null || true
        fi
    fi
done

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
    echo "DISPLAY: $DISPLAY"
    echo "XAUTHORITY: $XAUTHORITY"
    xauth list 2>/dev/null || echo "No xauth entries"
    echo "Testing with xeyes..."
    timeout 5 xeyes || echo "X11 test failed or timed out"
    exit 0
fi

# bash ./build_px4.sh
# bash ./build_microxrce.sh

exec "$@"
