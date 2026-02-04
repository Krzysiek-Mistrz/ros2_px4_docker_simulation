#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy
from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleCommand, VehicleLocalPosition, VehicleStatus
import time

class SimpleFlightNode(Node):

    def __init__(self):
        super().__init__('simple_flight_node')

        # === KONFIGURACJA QoS (Quality of Service) ===
        # PX4 wymaga profilu "Best Effort" dla większości tematów (np. statusu)
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )

        # === PUBLISHERS (WYSYŁANIE) ===
        # 1. Heartbeat trybu offboard - musi być wysyłany > 2Hz
        self.offboard_control_mode_publisher_ = self.create_publisher(
            OffboardControlMode, '/fmu/in/offboard_control_mode', 10)
        
        # 2. Zadawanie pozycji (gdzie dron ma lecieć)
        self.trajectory_setpoint_publisher_ = self.create_publisher(
            TrajectorySetpoint, '/fmu/in/trajectory_setpoint', 10)
        
        # 3. Komendy systemowe (uzbrajanie, zmiana trybu, lądowanie)
        self.vehicle_command_publisher_ = self.create_publisher(
            VehicleCommand, '/fmu/in/vehicle_command', 10)

        # === SUBSCRIBERS (ODBIERANIE) ===
        self.vehicle_local_position_subscriber_ = self.create_subscription(
            VehicleLocalPosition, '/fmu/out/vehicle_local_position', self.vehicle_local_position_callback, qos_profile)
        
        self.vehicle_status_subscriber_ = self.create_subscription(
            VehicleStatus, '/fmu/out/vehicle_status', self.vehicle_status_callback, qos_profile)

        # === ZMIENNE STANU ===
        self.offboard_setpoint_counter_ = 0
        self.vehicle_local_position = VehicleLocalPosition()
        self.vehicle_status = VehicleStatus()
        self.start_time = None 
        self.flight_state = "INIT" # INIT -> OFFBOARD -> ASCEND -> HOVER -> LAND

        # Timer główny pętli (10Hz czyli co 0.1s)
        self.timer = self.create_timer(0.1, self.timer_callback)
        self.get_logger().info("SimpleFlightNode uruchomiony. Czekam na połączenie z Pixhawk...")

    def vehicle_local_position_callback(self, vehicle_local_position):
        self.vehicle_local_position = vehicle_local_position

    def vehicle_status_callback(self, vehicle_status):
        self.vehicle_status = vehicle_status

    # === KOMENDY PX4 ===
    def arm(self):
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1.0)
        self.get_logger().info("Komenda: UZBRÓJ")

    def disarm(self):
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 0.0)
        self.get_logger().info("Komenda: ROZBRÓJ")

    def engage_offboard_mode(self):
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1.0, 6.0)
        self.get_logger().info("Komenda: TRYB OFFBOARD")

    def land(self):
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)
        self.get_logger().info("Komenda: LĄDOWANIE")

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

    # === GŁÓWNA PĘTLA STEROWANIA ===
    def timer_callback(self):
        # 1. Zawsze publikuj heartbeat trybu Offboard (wymagane przez PX4)
        offboard_msg = OffboardControlMode()
        offboard_msg.position = True
        offboard_msg.velocity = False
        offboard_msg.acceleration = False
        self.offboard_control_mode_publisher_.publish(offboard_msg)

        # Jeśli dopiero startujemy, wysyłamy kilka pustych setpointów, aby Pixhawk zaakceptował Offboard
        if self.offboard_setpoint_counter_ < 10:
            self.offboard_setpoint_counter_ += 1
            # Wysyłamy pozycję 0,0,0 (lub aktualną) żeby 'rozgrzać' łącze
            self.publish_position_setpoint(0.0, 0.0, 0.0)
            return

        # LOGIKA LOTU (MASZYNA STANÓW)
        if self.flight_state == "INIT":
            # Przełącz na Offboard i uzbrój
            self.engage_offboard_mode()
            self.arm()
            self.start_time = time.time()
            self.flight_state = "ASCEND"
            self.get_logger().info("Rozpoczynam wznoszenie na 1m...")

        elif self.flight_state == "ASCEND":
            # Wznoś się na 1 metr (w NED -1.0 to 1m w górę)
            # x=0, y=0 (startowa), z=-1.0
            self.publish_position_setpoint(0.0, 0.0, -1.0)
            
            # Sprawdź czy osiągnęliśmy wysokość (z tolerancją 20cm)
            current_alt = -1.0 * self.vehicle_local_position.z # konwersja na standardową wysokość
            if current_alt >= 0.90:
                self.get_logger().info("Osiągnięto pułap 1m. Czekam 5 sekund.")
                self.start_time = time.time() # Resetuj czas dla fazy HOVER
                self.flight_state = "HOVER"

        elif self.flight_state == "HOVER":
            # Utrzymuj pozycję
            self.publish_position_setpoint(0.0, 0.0, -1.0)

            # Czekaj 5 sekund
            elapsed = time.time() - self.start_time
            if elapsed > 5.0:
                self.get_logger().info("Czas minął. Lądowanie.")
                self.flight_state = "LAND"

        elif self.flight_state == "LAND":
            # Wyślij komendę lądowania (Pixhawk przejmie kontrolę i sam wyląduje)
            self.land()
            # Opcjonalnie: można zakończyć działanie noda lub czekać na rozbrojenie
            self.flight_state = "DONE"

        elif self.flight_state == "DONE":
            # Nic nie rób, Pixhawk ląduje.
            pass

    def publish_position_setpoint(self, x, y, z):
        msg = TrajectorySetpoint()
        msg.position = [x, y, z]
        msg.yaw = 0.0 # Opcjonalnie ustaw yaw (orientację) na północ (0)
        self.trajectory_setpoint_publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    simple_flight_node = SimpleFlightNode()
    rclpy.spin(simple_flight_node)
    simple_flight_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()