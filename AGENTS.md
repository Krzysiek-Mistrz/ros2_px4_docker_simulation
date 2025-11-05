# Repository Guidelines

## Project Structure & Module Organization

- Root files: `README.md`, `LICENSE`, `.gitignore`, `.gitmodules`
- Simulation stack in `drone_sim/`:
  - `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `entrypoint.sh`
  - PX4 and DDS sources: `PX4-Autopilot/`, `Micro-XRCE-DDS-Agent/`
  - ROS 2 workspace: `drone_sim/ws/`
    - Sources: `drone_sim/ws/src/`
      - `dron_nav_pkg/` (custom navigation node)
      - `px4_msgs/`, `px4_ros_com/` (PX4 ↔ ROS2 bridge and messages)
    - Build artifacts appear under `drone_sim/ws/{build,install,log}` at runtime

## Build, Test, and Development Commands

```bash
# Build and start container (host)
cd drone_sim && docker compose up --build

# Start container without rebuild (host)
cd drone_sim && docker compose up

# Get a shell inside the running container (host)
docker exec -it ros2_px4_sim bash

# Inside container: build PX4 (first run)
cd /home/px4/ros2 && bash ./build_px4.sh

# Inside container: build Micro XRCE-DDS (first run)
cd /home/px4/ros2/Micro-XRCE-DDS-Agent && mkdir -p build && cd build && cmake .. && make -j"$(nproc)"

# Inside container: build ROS2 workspace
cd /home/px4/ros2/ws && colcon build && source install/setup.bash

# Run the full stack helper (inside container)
cd /home/px4/ros2 && bash ./run_node.sh
```

## Coding Style & Naming Conventions

- Indentation: 4 spaces for Python (per `dron_nav_pkg/dron_nav_pkg/dron_nav_pkg.py`)
- File naming: Python modules are snake_case (e.g., `dron_nav_pkg.py`)
- Functions/variables: snake_case; classes: PascalCase (e.g., `Px4MissionNode`)
- Linting/formatting: ROS2 Python tooling is available in the image (`flake8`); package declares ament test deps in `package.xml`. Use `python3 -m flake8` if configured locally.

## Testing Guidelines

- Framework: ament/pytest (declared via `<test_depend>python3-pytest</test_depend>` and ament linters in `package.xml`)
- Test files: place under `drone_sim/ws/src/dron_nav_pkg/test/` using `pytest` naming (e.g., `test_*.py`)
- Running tests: after building the workspace, run `colcon test --packages-select dron_nav_pkg` inside the container
- Coverage: pytest-cov is present in image (`python3-pytest-cov`), but no explicit coverage threshold in the repo

## Commit & Pull Request Guidelines

- Conventional commits are not enforced. Recent examples:
  - "changed license"
  - "deleted old appimages from all history, and added appimages to gitignore"
  - "added qground control dependencies"
- PR process: Fork → feature branch → open PR (documented in README)
- Branch naming: not enforced; suggested: `feature/<name>`, `fix/<name>`

---

# Repository Tour

## 🎯 What This Repository Does

HydroLab 2 – ROS2 PX4 Drone Simulation provides a Dockerized environment to develop and test autonomous drone navigation using ROS2 Humble, PX4 Autopilot (v1.16.0), Gazebo, and a custom ROS 2 navigation node.

Key responsibilities:
- Provision a reproducible PX4 + Gazebo + ROS2 stack via Docker Compose
- Bridge PX4 and ROS2 through Micro-XRCE-DDS and px4_msgs/px4_ros_com
- Host a reference navigation node that performs an autonomous mission

---

## 🏗️ Architecture Overview

### System Context
```
Developer (host) → Docker Compose (drone_sim/) → Container (ros2_px4_sim)
                                         ↘ GUI/X11 → Gazebo + QGroundControl
ROS 2 Nodes (inside container) ↔ PX4 SITL ↔ Micro-XRCE-DDS Agent
```

### Key Components
- Docker runtime (drone_sim/Dockerfile, docker-compose.yml) – builds the ROS2/PX4 dev image with GUI and GPU support
- PX4 SITL (drone_sim/PX4-Autopilot) – flight stack simulated in Gazebo
- Micro-XRCE-DDS Agent (drone_sim/Micro-XRCE-DDS-Agent) – transports PX4 uORB data into ROS2 DDS
- ROS 2 workspace (drone_sim/ws) – houses `dron_nav_pkg`, `px4_msgs`, and `px4_ros_com`
- Navigation node (dron_nav_pkg/dron_nav_pkg/dron_nav_pkg.py) – implements a waypoint mission with Offboard control
- Entry scripts (entrypoint.sh, run_node.sh) – container bootstrap and end-to-end execution orchestration

### Data Flow
1. Micro-XRCE-DDS Agent opens UDP port 8888 and connects PX4 to DDS
2. PX4 SITL starts with Gazebo world and PX4 model (e.g., `gz_x500`)
3. ROS2 node publishes OffboardControlMode, TrajectorySetpoint, GotoSetpoint, VehicleCommand
4. PX4 streams VehicleLocalPosition, VehicleStatus, VehicleCommandAck to ROS2
5. Navigation node drives mission state machine and publishes mission status/phase

---

## 📁 Project Structure [Partial Directory Tree]

```
.
├── README.md
├── LICENSE
├── drone_sim/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── entrypoint.sh
│   ├── build_px4.sh
│   ├── build_microxrce.sh
│   ├── run_node.sh
│   ├── Micro-XRCE-DDS-Agent/
│   ├── PX4-Autopilot/
│   └── ws/
│       └── src/
│           ├── dron_nav_pkg/
│           │   ├── setup.py
│           │   ├── setup.cfg
│           │   ├── package.xml
│           │   └── dron_nav_pkg/
│           │       └── dron_nav_pkg.py
│           ├── px4_msgs/
│           └── px4_ros_com/
```

### Key Files to Know

| File | Purpose | When You'd Touch It |
|------|---------|---------------------|
| `drone_sim/docker-compose.yml` | Container config with X11, GPU, volumes | Change runtime env, mounts, or entry command |
| `drone_sim/Dockerfile` | Builds ROS2/PX4 image and installs QGroundControl | Add system deps or ROS tools |
| `drone_sim/entrypoint.sh` | X11 auth, environment sourcing | Adjust startup env sourcing |
| `drone_sim/run_node.sh` | Starts XRCE agent, PX4, then nav node | Modify orchestration or sequencing |
| `drone_sim/ws/src/dron_nav_pkg/dron_nav_pkg/dron_nav_pkg.py` | Mission node | Edit mission logic/parameters |
| `drone_sim/ws/src/dron_nav_pkg/setup.py` | ROS2 ament_python package config | Add console scripts/deps |
| `drone_sim/ws/src/dron_nav_pkg/package.xml` | Declares ROS2 deps and test deps | Manage dependencies and tests |
| `README.md` | End-user setup and workflow | Update docs |

---

## 🔧 Technology Stack

### Core Technologies
- Language: Python 3 (ROS2 nodes, mission logic)
- Framework: ROS 2 Humble (rclpy)
- Flight Stack: PX4 Autopilot v1.16.0 (SITL)
- Simulator: Gazebo (gz_x500 target)
- Middleware: Micro-XRCE-DDS Agent, Fast DDS (rmw-fastrtps-cpp)
- Containerization: Docker + Docker Compose with NVIDIA runtime and X11

### Key Libraries
- `px4_msgs` – PX4 ROS 2 message definitions consumed by the mission node
- `px4_ros_com` – Communication utilities between PX4 and ROS2
- `rclpy` – ROS 2 Python client library

### Development Tools
- `colcon` – ROS 2 build tool
- `pytest`/`ament` linters – testing and style checks
- `flake8` – Python linting (installed in image)

---

## 🌐 External Dependencies

- QGroundControl (AppImage symlinked to `qgroundcontrol` in image) – required to fully start PX4 in this setup
- NVIDIA drivers and `nvidia-docker2` – for Gazebo GPU acceleration
- X11 server on host – for GUI apps (Gazebo, QGroundControl)

### Environment Variables

- `ROS_DOMAIN_ID` – ROS 2 domain (default 0 via compose)
- `DISPLAY`, `QT_X11_NO_MITSHM`, `XAUTHORITY` – GUI/X11 configuration
- `NVIDIA_VISIBLE_DEVICES`, `NVIDIA_DRIVER_CAPABILITIES` – GPU access

---

## 🔄 Common Workflows

### Run everything automatically
- Inside the container: `bash /home/px4/ros2/run_node.sh`

### Manual step-by-step
- Start agent: `/home/px4/ros2/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent udp4 -p 8888`
- Start QGroundControl: `qgroundcontrol` (switch to user `px4` if needed)
- Start PX4 SITL: `cd /home/px4/ros2/PX4-Autopilot && make px4_sitl gz_x500`
- Run node: `ros2 run dron_nav_pkg dron_nav_pkg` or run the Python script directly

---

## 📈 Performance & Scale

- Use NVIDIA runtime and host networking for better Gazebo performance
- Keep Offboard setpoints streaming at ≥10 Hz (implemented by timer loop)

---

## 🚨 Things to Be Careful About

### Security Considerations
- GUI/X11 mounts expose display socket to container; use only on trusted hosts
- Privileged container is required by PX4/Gazebo setup; avoid running untrusted code inside

### Operational Notes
- The mission requires QGroundControl to be running for PX4 to fully initialize (documented in README)
- Ensure Micro-XRCE-DDS Agent is running before starting PX4 and the mission node


Last updated: 2025-11-02

*Update to last commit: e53263659066df927320709cc6948b82630b4863*