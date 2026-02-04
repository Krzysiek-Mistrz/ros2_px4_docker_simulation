#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy
from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleCommand, VehicleLocalPosition, VehicleStatus, VehicleCommandAck
import time

class SimpleFlightNode(Node):

    def __init__(self):
        super().__init__('simple_flight_node')

        # === KONFIGURACJA QoS ===
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )

        # === PUBLISHERS ===
        self.offboard_control_mode_publisher_ = self.create_publisher(
            OffboardControlMode, '/fmu/in/offboard_control_mode', 10)
        self.trajectory_setpoint_publisher_ = self.create_publisher(
            TrajectorySetpoint, '/fmu/in/trajectory_setpoint', 10)
        self.vehicle_command_publisher_ = self.create_publisher(
            VehicleCommand, '/fmu/in/vehicle_command', 10)

        # === SUBSCRIBERS ===
        self.vehicle_local_position_subscriber_ = self.create_subscription(
            VehicleLocalPosition, '/fmu/out/vehicle_local_position', self.vehicle_local_position_callback, qos_profile)
        
        # ZMIANA: Obsługa v1 (według Twojego topic list)
        self.vehicle_status_subscriber_ = self.create_subscription(
            VehicleStatus, '/fmu/out/vehicle_status_v1', self.vehicle_status_callback, qos_profile)
            
        # NOWOŚĆ: Nasłuchiwanie odpowiedzi (ACK) od PX4 - kluczowe do debugowania
        self.vehicle_command_ack_subscriber_ = self.create_subscription(
            VehicleCommandAck, '/fmu/out/vehicle_command_ack', self.vehicle_command_ack_callback, qos_profile)

        # === ZMIENNE STANU ===
        self.offboard_setpoint_counter_ = 0
        self.vehicle_local_position = VehicleLocalPosition()
        self.vehicle_status = VehicleStatus()
        self.start_time = None 
        self.flight_state = "INIT" 
        self.position_valid = False # Czy mamy już odczyt pozycji?

        # Timer (10Hz)
        self.timer = self.create_timer(0.1, self.timer_callback)
        self.get_logger().info("SimpleFlightNode ZAKTUALIZOWANY. Czekam na dane z PX4...")

    # === CALLBACKI ===
    def vehicle_local_position_callback(self, msg):
        self.vehicle_local_position = msg
        self.position_valid = True

    def vehicle_status_callback(self, msg):
        self.vehicle_status = msg

    def vehicle_command_ack_callback(self, msg):
        # Loguje tylko błędy lub odrzucenia komend
        if msg.result != 0: # 0 = ACCEPTED
            self.get_logger().error(f"KOMENDA ODRZUCONA! Cmd: {msg.command}, Result: {msg.result}")
        else:
            self.get_logger().info(f"Komenda przyjęta (Cmd: {msg.command})")

    # === KOMENDY POMOCNICZE ===
    def arm(self):
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1.0)
        self.get_logger().info("Wysyłam: UZBRÓJ")

    def engage_offboard_mode(self):
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1.0, 6.0)
        self.get_logger().info("Wysyłam: TRYB OFFBOARD")

    def land(self):
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)
        self.get_logger().info("Wysyłam: LĄDOWANIE")

    def publish_vehicle_command(self, command, param1=0.0, param2=0.0):
        msg = VehicleCommand()
        msg.param1 = param1
        msg.param2 = param2
        msg.command = command
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        self.vehicle_command_publisher_.publish(msg)

    def publish_position_setpoint(self, x, y, z):
        msg = TrajectorySetpoint()
        msg.position = [x, y, z]
        msg.yaw = 0.0 
        self.trajectory_setpoint_publisher_.publish(msg)

    # === GŁÓWNA PĘTLA (LOGIKA) ===
    def timer_callback(self):
        # 1. Heartbeat Offboard (musi iść zawsze)
        offboard_msg = OffboardControlMode()
        offboard_msg.position = True
        offboard_msg.velocity = False
        offboard_msg.acceleration = False
        self.offboard_control_mode_publisher_.publish(offboard_msg)

        # 2. Czekamy na "rozgrzanie" łącza i validację pozycji
        if self.offboard_setpoint_counter_ < 20:
            self.offboard_setpoint_counter_ += 1
            self.publish_position_setpoint(0.0, 0.0, 0.0)
            if self.offboard_setpoint_counter_ == 10:
                self.get_logger().info("Rozgrzewanie połączenia...")
            return

        if not self.position_valid:
             if self.offboard_setpoint_counter_ % 20 == 0:
                 self.get_logger().warn("Czekam na odczyt pozycji (VehicleLocalPosition)...")
             return

        # 3. Maszyna Stanów
        if self.flight_state == "INIT":
            # Próbuj przełączyć na Offboard i uzbroić
            # Sprawdzamy NavState (14 = Offboard) i ArmingState (2 = Armed)
            
            is_offboard = (self.vehicle_status.nav_state == 14)
            is_armed = (self.vehicle_status.arming_state == 2)

            if not is_offboard:
                self.engage_offboard_mode()
            
            if not is_armed:
                self.arm()
            
            # Jeśli oba warunki spełnione - lecimy
            if is_offboard and is_armed:
                self.start_time = time.time()
                self.flight_state = "ASCEND"
                self.get_logger().info("Dron GOTOWY! Zmieniam stan na ASCEND.")

        elif self.flight_state == "ASCEND":
            # Wznoś się na 1m (z = -1.0)
            self.publish_position_setpoint(0.0, 0.0, -1.0)
            
            current_alt = -1.0 * self.vehicle_local_position.z
            # Tolerancja 20cm
            if current_alt >= 0.8:
                self.get_logger().info(f"Pułap osiągnięty ({current_alt:.2f}m). Zwis.")
                self.start_time = time.time()
                self.flight_state = "HOVER"

        elif self.flight_state == "HOVER":
            self.publish_position_setpoint(0.0, 0.0, -1.0)
            
            elapsed = time.time() - self.start_time
            if elapsed > 5.0:
                self.get_logger().info("Koniec czasu. Lądowanie.")
                self.flight_state = "LAND"

        elif self.flight_state == "LAND":
            self.land()
            # Czekaj na rozbrojenie
            if self.vehicle_status.arming_state != 2:
                self.flight_state = "DONE"
                self.get_logger().info("Dron wylądował i rozbroił się.")

        elif self.flight_state == "DONE":
            pass

def main(args=None):
    rclpy.init(args=args)
    node = SimpleFlightNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
