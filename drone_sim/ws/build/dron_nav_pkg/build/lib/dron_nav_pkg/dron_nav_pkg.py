import math
import numpy as np
import threading
import time
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy
from px4_msgs.msg import OffboardControlMode
from px4_msgs.msg import TrajectorySetpoint, VehicleThrustSetpoint, VehicleLocalPosition
from px4_msgs.msg import VehicleStatus, VehicleCommand

class OffboardControl(Node):
    def __init__(self):
        super().__init__('square_flight')
        # Variables
        self.nav_state = VehicleStatus.NAVIGATION_STATE_MAX
        self.trajectory_msg = TrajectorySetpoint()
        self.uav_position = VehicleLocalPosition()
        timer_period = 0.02
        self.starting_attitude = -5.0
        self.armed = None
        self.velocity_control_ready = False
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
        # Publishers
        self.publisher_offboard_mode = self.create_publisher(OffboardControlMode, '/fmu/in/offboard_control_mode', qos_profile)
        self.publisher_trajectory = self.create_publisher(TrajectorySetpoint, '/fmu/in/trajectory_setpoint', qos_profile)
        self.publisher_thrust = self.create_publisher(VehicleThrustSetpoint, '/fmu/in/vehicle_thrust_setpoint', qos_profile)
        self.publisher_command = self.create_publisher(VehicleCommand, '/fmu/in/vehicle_command', qos_profile)
        # Subscribers
        self.uav_position = self.create_subscription(VehicleLocalPosition, '/fmu/out/vehicle_local_position', self.vehicle_position_callback, qos_profile)
        self.status_sub = self.create_subscription(VehicleStatus, '/fmu/out/vehicle_status', self.vehicle_status_callback, qos_profile)
        # Main Logic
        self.timer = self.create_timer(timer_period, self.main)
        self.spin_thread = threading.Thread(target=rclpy.spin, args=(self,), daemon=True)
        self.spin_thread.start()
        self.square_flight()
 
    def vehicle_position_callback(self, msg):
        self.uav_position = msg
        self.velocity_control_ready = self.velocity_control_ready or np.abs(self.starting_attitude - self.uav_position.z) < 0.05

    def vehicle_status_callback(self, msg):
        self.armed = True if 2 == msg.arming_state else False
        self.nav_state = msg.nav_state

    def square_flight(self):
        while rclpy.ok():
            if self.velocity_control_ready:
                yaw_rad = self.uav_position.heading
                self.trajectory_msg.velocity[0] = math.cos(yaw_rad)
                self.trajectory_msg.velocity[1] = math.sin(yaw_rad)
                self.trajectory_msg.velocity[2] = 0.0
                self.trajectory_msg.position[0] = None
                self.trajectory_msg.position[1] = None
                self.trajectory_msg.position[2] = None
                self.get_logger().info('Moving forward...')
                time.sleep(4)
                self.trajectory_msg.yaw += math.pi/2
                self.trajectory_msg.velocity[0] = 0.0
                self.trajectory_msg.velocity[1] = 0.0
                self.trajectory_msg.velocity[2] = 0.0
                self.trajectory_msg.position[0] = None
                self.trajectory_msg.position[1] = None
                self.trajectory_msg.position[2] = None
                self.get_logger().info('Turning...')
                time.sleep(1)

    def main(self):
        if not self.velocity_control_ready:
            self.set_control_mode('position')
            self.trajectory_msg.position[0] = 0
            self.trajectory_msg.position[1] = 0
            self.trajectory_msg.position[2] = self.starting_attitude
        else:
            self.set_control_mode('velocity')
            self.velocity_control_ready = True
        self.publisher_trajectory.publish(self.trajectory_msg)
        if self.armed == False:
            self.vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1.0)
            self.vehicle_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1.0, 6.0)

    def vehicle_command(self, command, param1=0.0, param2=0.0):
        command_msg = VehicleCommand()
        command_msg.timestamp = int(Clock().now().nanoseconds / 1000)
        command_msg.param1 = param1
        command_msg.param2 = param2
        command_msg.target_system = 1
        command_msg.command = command
        command_msg.target_component = 1
        command_msg.source_system = 1
        command_msg.source_component = 1
        command_msg.from_external = True
        self.publisher_command.publish(command_msg)

    def set_control_mode(self, command):
        offboard_msg = OffboardControlMode()
        offboard_msg.timestamp = int(Clock().now().nanoseconds / 1000)
        offboard_msg.position = True if command=='position' else False
        offboard_msg.velocity = True if command=='velocity' else False
        offboard_msg.acceleration=  True if command=='acceleration' else False
        offboard_msg.body_rate = True if command=='body_rate' else False
        offboard_msg.attitude = True if command=='attitude' else False
        offboard_msg.thrust_and_torque = True if command=='thrust_and_torque' else False
        self.publisher_offboard_mode.publish(offboard_msg)

def main(args=None):
    rclpy.init(args=args)
    offboard_control = OffboardControl()
    rclpy.spin(offboard_control)
    offboard_control.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()