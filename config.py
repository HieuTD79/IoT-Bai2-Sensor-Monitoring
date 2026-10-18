import os
from dotenv import load_dotenv

load_dotenv()
MQTT_HOST = os.getenv("MQTT_HOST", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "ptit/b23dccn311/iot_bai2/telemetry")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "iot-bai2-collector-b23dccn311")
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_ORG = os.getenv("INFLUX_ORG", "ptit")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "iot_bai2")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
DEVICE_ID = os.getenv("DEVICE_ID", "ESP32-B23DCCN311")
NUMERIC_FIELDS = ["temperature", "humidity", "distance_cm", "rssi", "sequence", "uptime_s"]
