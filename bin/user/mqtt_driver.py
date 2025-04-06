# File: mqtt_driver.py

import json
import threading
import queue
import time
import datetime
import weewx.drivers
import logging
import paho.mqtt.client as mqtt

DRIVER_NAME = 'MQTTDriver'
DRIVER_VERSION = '0.3'

log = logging.getLogger(__name__)

class MQTTDriver(weewx.drivers.AbstractDevice):
    """WeeWX driver that subscribes to MQTT messages and parses the output."""

    def __init__(self, **stn_dict):
        """Initialize the driver with station configuration from weewx.conf."""
        self.host = stn_dict['host']  # Required
        self.port = int(stn_dict.get('port', 1883))
        self.topic = stn_dict['topic']  # Required
        self.poll_interval = float(stn_dict.get('poll_interval', 5.0))
        self.username = stn_dict.get('username', None)
        self.password = stn_dict.get('password', None)
        self.client_id = stn_dict.get('client_id', None)
        self.keepalive = int(stn_dict.get('keepalive', 60))
        self.qos = int(stn_dict.get('qos', 0))
        self.tls = stn_dict.get('tls', False)  # True or False
        self.cert_path = stn_dict.get('cert_path', None)  # Path to CA cert if using TLS

        # Load the model mappings from the configuration
        self.model_mappings = stn_dict.get('model_mappings', {})

        self._stop_event = threading.Event()
        self._queue = queue.Queue()

        self.last_seen_packets = set()  # Set to track unique (time, model, id) tuples
        self.packet_timestamps = {}  # Dictionary to store packet timestamps for pruning

        # MQTT client setup
        self.client = mqtt.Client(client_id=self.client_id)
        if self.username is not None:
            self.client.username_pw_set(self.username, self.password)
        if self.tls:
            if self.cert_path:
                self.client.tls_set(ca_certs=self.cert_path)
            else:
                self.client.tls_set()

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        self.client.connect(self.host, self.port, self.keepalive)

        self.client.loop_start()
        log.info(f"{DRIVER_NAME} initialized with host={self.host}, topic={self.topic}")

    @property
    def hardware_name(self):
        """Return the name of the hardware."""
        return "MQTT Driver"

    def genLoopPackets(self):
        """Generator function that yields loop packets to WeeWX."""
        while not self._stop_event.is_set():
            try:
                data = self._queue.get(timeout=self.poll_interval)
                packet = self._parse_data(data)
                if packet:
                    log.debug(f"Yielding packet: {packet}")
                    yield packet
            except queue.Empty:
                pass

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when the client connects to the broker."""
        if rc == 0:
            log.info("Connected to MQTT broker")
            client.subscribe(self.topic, qos=self.qos)
            log.info(f"Subscribed to topic: {self.topic}")
        else:
            log.error(f"Failed to connect to MQTT broker, return code {rc}")

    def _on_message(self, client, userdata, msg):
        """Callback when a message is received from the broker."""
        try:
            payload = msg.payload.decode('utf-8')
            log.debug(f"Received message: {payload}")
            self._queue.put(payload)
        except Exception as e:
            log.error(f"Error decoding message payload: {e}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback when the client disconnects from the broker."""
        log.info("Disconnected from MQTT broker")

    def _parse_data(self, data):
        """Parse JSON data from the MQTT message and map it to WeeWX fields based on the model-specific configuration."""
        try:
            json_data = json.loads(data)
            model = json_data.get('model')
            device_id = json_data.get('id')
            timestamp = json_data.get('time')
            message_type = json_data.get('message_type')

            # Parse the date from the timestamp (assuming it is in "YYYY-MM-DD HH:MM:SS" format)
            current_time = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            current_day = current_time.date()

            # Check if we have a mapping for the specific model
            if not model or model not in self.model_mappings:
                log.warning(f"No field mappings found for model: {model}")
                return None

            # Create a unique identifier (tuple) for this packet to detect duplicates
            packet_id = (timestamp, model, device_id, message_type)

            # Clean up old packets (e.g., those older than 10 seconds)
            cutoff_time = datetime.datetime.now() - datetime.timedelta(seconds=10)
            self.last_seen_packets = {pkt for pkt in self.last_seen_packets if self.packet_timestamps.get(pkt, current_time) > cutoff_time}

            if packet_id in self.last_seen_packets:
                log.debug(f"Duplicate packet received for {packet_id}, ignoring.")
                return None
            else:
                self.last_seen_packets.add(packet_id)
                self.packet_timestamps[packet_id] = current_time

            # Get the field mappings for the detected model
            field_mappings = self.model_mappings[model]

            packet = {}
            packet['dateTime'] = int(time.time())
            packet['usUnits'] = weewx.US

            # Apply the mappings
            for weewx_field, json_key in field_mappings.items():
                if json_key in json_data:
                    try:
                        value = float(json_data[json_key])
                        packet[weewx_field] = value
                    except ValueError:
                        log.error(f"Error converting field {json_key}: {json_data[json_key]} to float")

            return packet
        except Exception as e:
            log.error(f"Error parsing data: {e}")
            return None

    def closePort(self):
        """Clean up resources and stop the MQTT client."""
        log.info("Stopping MQTT Driver")
        self._stop_event.set()
        self.client.loop_stop()
        self.client.disconnect()


def loader(config_dict, _):
    """Loader function required by WeeWX to instantiate the driver."""
    driver_config = config_dict.get('MQTTDriver', {})
    if not driver_config.get('host') or not driver_config.get('topic'):
        raise ValueError("Both 'host' and 'topic' must be specified in the configuration.")
    
    # Load model-specific field mappings
    model_mappings_config = config_dict.get('ModelMappings', {})
    driver_config['model_mappings'] = model_mappings_config

    return MQTTDriver(**driver_config)

