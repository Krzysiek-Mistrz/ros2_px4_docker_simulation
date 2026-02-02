# HydroLab 2 - ROS2 PX4 Drone Simulation

A comprehensive Docker-based simulation environment for autonomous drone development using ROS2 Humble, PX4 Autopilot, and Gazebo. This project provides a complete setup for developing and testing drone navigation algorithms in a containerized environment.

## Project Overview

This project creates a fully containerized drone simulation environment that includes:
- **PX4 Autopilot v1.16.0** - Flight control software
- **ROS2 Humble** - Robot Operating System for communication
- **Gazebo** - 3D simulation environment
- **Micro-XRCE-DDS-Agent** - Communication bridge between PX4 and ROS2
- **QGroundControl** - Ground control station for monitoring and control
- **Custom Navigation Package** - Autonomous mission control

## Project Structure

```
hydrolab_2/
├── drone_sim/                          # Main simulation directory
│   ├── Dockerfile                      # Container configuration
│   ├── docker-compose.yml              # Docker Compose setup
│   ├── entrypoint.sh                   # Container entry point
│   ├── build_px4.sh                    # PX4 installation script
│   ├── build_microxrce.sh              # Micro-XRCE-DDS setup script
│   ├── run_node.sh                     # Mission execution script
│   ├── instruction_correctly_install_px4.md  # PX4 installation notes
│   ├── Micro-XRCE-DDS-Agent/           # DDS communication agent (submodule)
│   ├── PX4-Autopilot/                  # PX4 flight stack (auto-cloned)
│   └── ws/                             # ROS2 workspace
│       ├── src/
│       │   ├── dron_nav_pkg/           # Custom drone navigation package
│       │   ├── px4_msgs/               # PX4 message definitions
│       │   └── px4_ros_com/            # PX4-ROS2 communication bridge
│       ├── build/                      # Build artifacts
│       ├── install/                    # Installed packages
│       └── log/                        # Build logs
├── QGroundControl.AppImage             # Ground control station
└── README.md                           # This file
```

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04/22.04 or compatible Linux distribution
- **Docker**: Version 20.10 or later
- **Docker Compose**: Version 2.0 or later
- **NVIDIA GPU**: Required for Gazebo simulation (with nvidia-docker2)
- **X11**: For GUI applications

### Required Software
```bash
# Install Docker
sudo apt update
sudo apt install docker.io docker-compose-plugin

# Install NVIDIA Docker support (for GPU acceleration)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update && sudo apt install nvidia-docker2
sudo systemctl restart docker

# Add user to docker group
sudo usermod -aG docker $USER
```

## Quick Start

### 1. Clone the Repository
```bash
git clone --recursive https://github.com/your-username/hydrolab_2.git
cd hydrolab_2
```

### 2. Setup X11 for GUI Applications !IMPORTANT!
```bash
# Allow Docker to access X11 display
xhost +local:
```

### 3. Build and Start the Container
```bash
cd drone_sim
docker compose up --build
```

### 3'. If you want only to Start the Container
```bash
cd drone_sim
docker compose up
```
> *NOTE*
> *closing is on ctrl+c*

### 4. Access the Container
```bash
# In a new terminal
docker exec -it ros2_px4_sim bash
```

### 5. Build the Simulation Environment
```bash
# Inside the container
cd /home/px4/ros2

# Build PX4 (first time only)
bash ./build_px4.sh

# Build Micro-XRCE-DDS Agent (first time only)
cd Micro-XRCE-DDS-Agent
mkdir -p build && cd build
cmake ..
make -j$(nproc)
cd ../..

# Build ROS2 workspace
cd ws
colcon build
source install/setup.bash
```

## Running the Simulation

### Method 1: Automated Mission Execution
```bash
# Inside the container
cd /home/px4/ros2
bash ./run_node.sh
```

This script will:
1. Start the Micro-XRCE-DDS Agent
2. Launch PX4 SITL with Gazebo
3. Execute the autonomous mission

**Note**: After starting the Micro-XRCE-DDS Agent, you should also start QGroundControl for monitoring:
```bash
# In a separate terminal inside the container
qgroundcontrol
```

### Method 2: Manual Step-by-Step Execution

#### Terminal 1: Start Micro-XRCE-DDS Agent
```bash
cd /home/px4/ros2/Micro-XRCE-DDS-Agent/build
./MicroXRCEAgent udp4 -p 8888
```

#### Terminal 2: Start QGroundControl (!IMPORTANT!)
change to normal user:  
```bash
su px4
```  

install all deps and qground control:  
```bash
qgroundcontrol_install.sh
```  

After that you should change permissions for pixhawk com port (please check your com port after connecting pixhawk to your device):  
```bash
sudo chmod 666 /dev/ttyACM0
sudo chmod 666 /dev/ttyACM1
```  

Start QgroundControl:  
```bash
QGroundControl-x86_64.AppImage
```  

> *Note!*
> *Without QGroundControl the PX4 doesn't start*
> *U also have to switch up to normal user to use QGround control in docker*

#### Terminal 3: Start PX4 Simulation
```bash
cd /home/px4/ros2/PX4-Autopilot
make px4_sitl gz_x500
```

#### Terminal 4: Run ROS2 Navigation Node
```bash
cd /home/px4/ros2/ws
source install/setup.bash
python3 src/dron_nav_pkg/dron_nav_pkg/dron_nav_pkg.py

or

ros2 run dron_nav_pkg dron_nav_pkg
```

## Mission Description

The autonomous mission performs the following sequence:

1. **Takeoff and Navigate to Point A** (5m forward, 2m up from start)
2. **Hover at Point A** (5 seconds)
3. **Descend** (1 meter down)
4. **Hover at Lower Altitude** (5 seconds)
5. **Ascend** (back to Point A altitude)
6. **Return to Home** (original starting position)

### Mission Parameters (Configurable)
- **Point A Offset**: `(5.0, 0.0, -2.0)` meters from start
- **Descent Distance**: `1.0` meter
- **Hover Duration**: `5.0` seconds at each waypoint
- **Position Threshold**: `0.3` meters for waypoint acceptance

## ROS2 Topics

### Published Topics
- `/fmu/in/goto_setpoint` - High-level position commands
- `/fmu/in/trajectory_setpoint` - Low-level trajectory commands
- `/fmu/in/offboard_control_mode` - Offboard mode configuration
- `/fmu/in/vehicle_command` - Vehicle commands (arm, mode changes)
- `/mission/phase` - Current mission phase (1-7)
- `/mission/status` - Mission completion status

### Subscribed Topics
- `/fmu/out/vehicle_local_position` - Current drone position
- `/fmu/out/vehicle_command_ack` - Command acknowledgments
- `/fmu/out/vehicle_status` - Vehicle status information

## Configuration

### Environment Variables
```bash
export ROS_DOMAIN_ID=0          # ROS2 domain
export DISPLAY=:1               # X11 display for GUI
export QT_X11_NO_MITSHM=1      # Qt compatibility
```

### Docker Compose Configuration
The `docker-compose.yml` includes:
- NVIDIA GPU support
- X11 forwarding for Gazebo GUI
- Host networking for ROS2 communication
- Volume mounting for persistent development

## Troubleshooting

### Common Issues

#### 1. Gazebo Won't Start
```bash
# Check NVIDIA drivers
nvidia-smi

# Verify X11 forwarding
echo $DISPLAY
xhost +local:docker
```

#### 2. PX4 Connection Issues
```bash
# Check if Micro-XRCE-DDS Agent is running
ps aux | grep MicroXRCEAgent

# Verify port availability
netstat -tulpn | grep 8888
```

#### 3. ROS2 Communication Problems
```bash
# Check ROS2 environment
ros2 topic list
ros2 node list

# Verify domain ID
echo $ROS_DOMAIN_ID
```

#### 4. Build Failures
```bash
# Clean and rebuild ROS2 workspace
cd /home/px4/ros2/ws
rm -rf build install log
colcon build

# Clean PX4 build
cd /home/px4/ros2/PX4-Autopilot
make clean
make px4_sitl gz_x500
```

### Log Files
- PX4 logs: `/tmp/px4_sitl.log`
- ROS2 logs: `ws/log/`
- Container logs: `docker logs ros2_px4_sim`

## Development Workflow

### 1. Modifying the Navigation Algorithm
```bash
# Edit the navigation node
nano ws/src/dron_nav_pkg/dron_nav_pkg/dron_nav_pkg.py

# Rebuild the package
cd ws
colcon build --packages-select dron_nav_pkg
source install/setup.bash
```

### 2. Adding New ROS2 Packages
```bash
cd ws/src
ros2 pkg create --build-type ament_python my_new_package
# Edit package files...
cd ..
colcon build
```

### 3. Testing Changes
```bash
# Run individual components for testing
ros2 run dron_nav_pkg dron_nav_pkg

# Monitor topics
ros2 topic echo /fmu/out/vehicle_local_position
ros2 topic echo /mission/phase
```

## Additional Resources

### Documentation
- [PX4 User Guide](https://docs.px4.io/)
- [ROS2 Documentation](https://docs.ros.org/en/humble/)
- [Gazebo Documentation](https://gazebosim.org/docs)

### Useful Commands
```bash
# QGroundControl (recommended for monitoring)
qgroundcontrol
# Or directly:
/opt/QGroundControl.AppImage

# Monitor ROS2 topics
ros2 topic list
ros2 topic echo /fmu/out/vehicle_local_position

# Check PX4 status
cd PX4-Autopilot
make px4_sitl jmavsim  # Alternative simulator
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [PX4 Development Team](https://px4.io/) for the flight control software
- [ROS2 Community](https://ros.org/) for the robotics middleware
- [eProsima](https://www.eprosima.com/) for Micro-XRCE-DDS
- [Open Source Robotics Foundation](https://www.openrobotics.org/) for Gazebo

---

**Note**: This simulation environment is designed for development and testing purposes. Always follow proper safety procedures when working with real drone hardware.