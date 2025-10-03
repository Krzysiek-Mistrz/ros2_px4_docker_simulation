#!/usr/bin/env python3
import time
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy
from px4_msgs.msg import (
    GotoSetpoint,
    VehicleLocalPosition,
    TrajectorySetpoint,
    OffboardControlMode,
    VehicleCommand,
    VehicleCommandAck,
    VehicleStatus,
)
from std_msgs.msg import Float32MultiArray, Bool

# fallback numeric commands (kept for compatibility)
CMD_DO_SET_MODE = 176   # MAV_CMD_DO_SET_MODE
CMD_ARM = 400           # MAV_CMD_COMPONENT_ARM_DISARM

class Px4MissionNode(Node):
    def __init__(self):
        super().__init__('px4_mission_node_merged_start')

        # QoS best-effort for PX4 topics
        self.qos_be = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
            durability=QoSDurabilityPolicy.VOLATILE,
        )

        # Publishers
        self.goto_pub = self.create_publisher(GotoSetpoint, '/fmu/in/goto_setpoint', self.qos_be)
        self.traj_pub = self.create_publisher(TrajectorySetpoint, '/fmu/in/trajectory_setpoint', 10)
        self.offb_mode_pub = self.create_publisher(OffboardControlMode, '/fmu/in/offboard_control_mode', 10)
        self.cmd_pub = self.create_publisher(VehicleCommand, '/fmu/in/vehicle_command', 10)

        self.phase_pub = self.create_publisher(Float32MultiArray, '/mission/phase', 10)
        self.status_pub = self.create_publisher(Bool, '/mission/status', 10)

        # Subscribers
        self.create_subscription(VehicleLocalPosition, '/fmu/out/vehicle_local_position', self.pos_cb, self.qos_be)
        # ack subscription (optional, useful for debugging arm acceptance)
        self.create_subscription(VehicleCommandAck, '/fmu/out/vehicle_command_ack', self._cmd_ack_cb, 10)
        # vehicle status (to know nav_state and whether OFFBOARD is active)
        self.create_subscription(VehicleStatus, '/fmu/out/vehicle_status', self._vehicle_status_cb, self.qos_be)

        # mission parameters (tweak)
        self.point_a_rel = (5.0, 0.0, -2.0)
        self.descend_by = 1.0
        self.hover_at_a_sec = 5.0
        self.hover_low_sec = 5.0
        self.pos_threshold = 0.3

        # state
        self.current_pos = None
        self.start_pos = None
        self.point_a = None
        self.target = None
        self.state = 'WAIT_START_POS'
        self.wait_start_time = None

        # offboard/arming helpers
        self._setpoints_sent = 0
        self._sent_arm = False
        self._warmup_start = None

        # vehicle status store
        self.vehicle_status = None
        self.is_at_target_altitude = False

        # main timer: 10 Hz — we must stream offboard messages continuously
        self.timer = self.create_timer(0.1, self._update)

        self.get_logger().info('Px4MissionNode (merged start) started — waiting for vehicle_local_position...')

    # -------------------------
    # Callbacks
    # -------------------------
    def pos_cb(self, msg: VehicleLocalPosition):
        self.current_pos = msg
        if self.start_pos is None:
            self.start_pos = (msg.x, msg.y, msg.z)
            self.point_a = (
                self.start_pos[0] + self.point_a_rel[0],
                self.start_pos[1] + self.point_a_rel[1],
                self.start_pos[2] + self.point_a_rel[2],
            )
            self.get_logger().info(f"Captured start_pos: {self.start_pos}, point A: {self.point_a}")

    def _cmd_ack_cb(self, ack: VehicleCommandAck):
        # log ack for arm/commands to help debugging arm acceptance
        self.get_logger().info(f"Cmd ACK: command={ack.command} result={ack.result} (progress={ack.progress})")

    def _vehicle_status_cb(self, msg: VehicleStatus):
        self.vehicle_status = msg
        # optional tiny debug
        # self.get_logger().debug(f"VehicleStatus.nav_state={getattr(msg, 'nav_state', None)}")

    # -------------------------
    # telemetry helpers
    # -------------------------
    def publish_phase(self, n: int):
        self.phase_pub.publish(Float32MultiArray(data=[float(n)]))

    def publish_status(self, done: bool):
        self.status_pub.publish(Bool(data=done))

    # -------------------------
    # goto / trajectory helpers
    # -------------------------
    def send_goto(self, target):
        g = GotoSetpoint()
        tx, ty, tz = float(target[0]), float(target[1]), float(target[2])
        if hasattr(g, 'x') and hasattr(g, 'y') and hasattr(g, 'z'):
            g.x, g.y, g.z = tx, ty, tz
        elif hasattr(g, 'position'):
            try:
                g.position = [tx, ty, tz]
            except Exception:
                try:
                    g.position[0], g.position[1], g.position[2] = tx, ty, tz
                except Exception:
                    pass
        self.goto_pub.publish(g)
        self.get_logger().info(f"[GOTO] x:{tx:.2f} y:{ty:.2f} z:{tz:.2f}")

    def publish_trajectory_setpoint(self, target):
        if target is None:
            return

        tx, ty, tz = float(target[0]), float(target[1]), float(target[2])
        t = TrajectorySetpoint()

        # set timestamp in microseconds (many px4 bridges expect us)
        try:
            t.timestamp = int(self.get_clock().now().nanoseconds // 1000)
        except Exception:
            try:
                t.timestamp = int(time.time() * 1_000_000)
            except Exception:
                pass

        published = False

        # preferred: .position list/array
        if hasattr(t, 'position'):
            try:
                t.position = [tx, ty, tz]
                self.traj_pub.publish(t)
                published = True
            except Exception:
                try:
                    t.position[0], t.position[1], t.position[2] = tx, ty, tz
                    self.traj_pub.publish(t)
                    published = True
                except Exception:
                    self.get_logger().warning("Could not assign to TrajectorySetpoint.position")

        # fallback: direct x,y,z fields
        if not published and hasattr(t, 'x') and hasattr(t, 'y') and hasattr(t, 'z'):
            try:
                t.x, t.y, t.z = tx, ty, tz
                self.traj_pub.publish(t)
                published = True
            except Exception as e:
                self.get_logger().warning(f"Failed assign x/y/z to TrajectorySetpoint: {e}")

        # final fallback: try any attribute with 'pos'/'position' in name
        if not published:
            for attr in dir(t):
                if 'pos' in attr.lower():
                    try:
                        val = getattr(t, attr)
                        try:
                            val[0], val[1], val[2] = tx, ty, tz
                            setattr(t, attr, val)
                        except Exception:
                            setattr(t, attr, [tx, ty, tz])
                        self.traj_pub.publish(t)
                        published = True
                        break
                    except Exception:
                        continue

        if published:
            self._setpoints_sent += 1
        else:
            self.get_logger().warning(
                "Unable to set position on TrajectorySetpoint; run 'ros2 interface show px4_msgs/msg/TrajectorySetpoint' "
                "and adapt fields if needed."
            )

    # -------------------------
    # offboard / vehicle command helpers (start logic przeniesione)
    # -------------------------
    def publish_offboard_mode(self):
        m = OffboardControlMode()
        # keep position control enabled for mission (TrajectorySetpoint.position)
        try:
            m.position = True
            m.velocity = False
            m.acceleration = False
            m.attitude = False
            m.body_rate = False
        except Exception:
            pass
        # timestamp (microseconds) if present
        try:
            m.timestamp = int(self.get_clock().now().nanoseconds // 1000)
        except Exception:
            try:
                m.timestamp = int(time.time() * 1_000_000)
            except Exception:
                pass
        self.offb_mode_pub.publish(m)

    def publish_vehicle_command(self, command, param1=0.0, param2=0.0):
        msg = VehicleCommand()
        try:
            # allow command to be either int or enum-like constant on the class
            msg.command = int(command)
        except Exception:
            # fallback: try attributes or numeric
            try:
                msg.command = command
            except Exception:
                msg.command = 0
        msg.param1 = float(param1)
        msg.param2 = float(param2)
        # conventional addressing
        try:
            msg.target_system = 1
            msg.target_component = 1
        except Exception:
            pass
        try:
            msg.source_system = 1
            msg.source_component = 1
        except Exception:
            pass
        # mark external and timestamp if fields exist
        try:
            msg.from_external = True
        except Exception:
            pass
        try:
            msg.timestamp = int(self.get_clock().now().nanoseconds // 1000)
        except Exception:
            try:
                msg.timestamp = int(time.time() * 1_000_000)
            except Exception:
                pass
        self.cmd_pub.publish(msg)
        self.get_logger().info(f"Sent vehicle_command {msg.command} p1={param1} p2={param2}")

    def arm(self):
        # prefer symbolic constant if available
        try:
            arm_cmd = VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM
        except Exception:
            arm_cmd = CMD_ARM
        self.publish_vehicle_command(arm_cmd, param1=1.0)
        self.get_logger().info("Wysłano komendę uzbrojenia (arm)")

    def engage_offboard_mode(self):
        # prefer symbolic constant if available
        try:
            do_set_mode_cmd = VehicleCommand.VEHICLE_CMD_DO_SET_MODE
        except Exception:
            do_set_mode_cmd = CMD_DO_SET_MODE
        # param1=1.0 (custom mode), param2=6.0 (OFFBOARD in many PX4 builds)
        self.publish_vehicle_command(do_set_mode_cmd, param1=1.0, param2=6.0)
        self.get_logger().info("Wysłano żądanie przełączenia w tryb Offboard (DO_SET_MODE)")

    # -------------------------
    # utilities
    # -------------------------
    def reached_target(self, target):
        if self.current_pos is None or target is None:
            return False
        dx = abs(self.current_pos.x - float(target[0]))
        dy = abs(self.current_pos.y - float(target[1]))
        dz = abs(self.current_pos.z - float(target[2]))
        return (dx <= self.pos_threshold) and (dy <= self.pos_threshold) and (dz <= self.pos_threshold)

    # -------------------------
    # main periodic update (10 Hz)
    # -------------------------
    def _update(self):
        # ensure warmup timer starts
        if self._warmup_start is None:
            self._warmup_start = time.monotonic()

        # Always stream offboard mode and a setpoint (if target) at 10 Hz
        self.publish_offboard_mode()
        if self.target is not None:
            self.publish_trajectory_setpoint(self.target)

        # After ~10 setpoints, request DO_SET_MODE + ARM (same logic as before but now uses helper funcs)
        if not self._sent_arm and self._setpoints_sent >= 10:
            self.get_logger().info("Wysyłanie żądania Offboard + arm (po 10 setpointach).")
            self.engage_offboard_mode()
            # small delay not needed here because messages are published continuously in subsequent ticks
            self.arm()
            self._sent_arm = True

        # Optional: if vehicle_status indicates OFFBOARD, we could switch to velocity-based ascend,
        # but original mission uses position setpoints so we keep original mission flow.

        # --- mission state machine (unchanged logic) ---
        if self.state == 'WAIT_START_POS':
            if self.start_pos is not None:
                self.get_logger().info('Start position available -> flying to Point A')
                self.state = 'FLY_TO_A'
                self.publish_phase(1)
                self.target = self.point_a
                self.send_goto(self.target)
            return

        if self.state == 'FLY_TO_A':
            if self.reached_target(self.target):
                self.get_logger().info('Reached Point A')
                self.state = 'HOVER_AT_A'
                self.publish_phase(2)
                self.wait_start_time = time.monotonic()
            return

        if self.state == 'HOVER_AT_A':
            if time.monotonic() - self.wait_start_time >= self.hover_at_a_sec:
                self.get_logger().info('Hover at A done -> descending')
                self.state = 'DESCEND'
                self.publish_phase(3)
                z_lower = self.point_a[2] - self.descend_by
                self.target = (self.point_a[0], self.point_a[1], z_lower)
                self.send_goto(self.target)
            return

        if self.state == 'DESCEND':
            if self.reached_target(self.target):
                self.get_logger().info('Descended to lower altitude')
                self.state = 'HOVER_LOW'
                self.publish_phase(4)
                self.wait_start_time = time.monotonic()
            return

        if self.state == 'HOVER_LOW':
            if time.monotonic() - self.wait_start_time >= self.hover_low_sec:
                self.get_logger().info('Hover low done -> ascending to A')
                self.state = 'ASCEND'
                self.publish_phase(5)
                self.target = (self.point_a[0], self.point_a[1], self.point_a[2])
                self.send_goto(self.target)
            return

        if self.state == 'ASCEND':
            if self.reached_target(self.target):
                self.get_logger().info('Ascended back to Point A -> returning home')
                self.state = 'RETURN'
                self.publish_phase(6)
                self.target = self.start_pos
                self.send_goto(self.target)
            return

        if self.state == 'RETURN':
            if self.reached_target(self.target):
                self.get_logger().info('Returned to start position -> mission complete')
                self.publish_status(True)
                self.publish_phase(7)
                self.state = 'DONE'
            return

        # DONE: do nothing but keep streaming to avoid PX4 dropping OFFBOARD
        if self.state == 'DONE':
            return


def main(args=None):
    rclpy.init(args=args)
    node = Px4MissionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
