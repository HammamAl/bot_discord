import os
from typing import Final
from dotenv import load_dotenv

# --- Discord Config ---
load_dotenv()
DISCORD_TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")
CHANNEL_ID: Final[int] = int(os.getenv("CHANNEL_ID"))  # ID saluran Discord tempat bot mengirim notifikasi
CHANNEL_NAME: Final[str] = os.getenv("CHANNEL_NAME")  # Nama saluran Discord (opsional, untuk validasi)

# ESP32 Config
AMONIA_AMBANG_BATAS = 30  # Ambang batas Amonia untuk memicu notifikasi otomatis

# MQTT Config
MQTT_BROKER: Final[str] = os.getenv("MQTT_BROKER")
MQTT_PORT: Final[int] = int(os.getenv("MQTT_PORT")) # Port untuk koneksi TLS
MQTT_USER: Final[str] = os.getenv("MQTT_USER")
MQTT_PASSWORD: Final[str] = os.getenv("MQTT_PASSWORD")
MQTT_TOPIC_RELAY_STATUS = "relay/notifications"  # Topik untuk pemberitahuan relay
MQTT_RELAY_CONTROL_TOPIC = "esp32/relay"  # Topik kontrol relay
MQTT_SENSOR_DATA_TOPIC =  "sensor/data" # Topik data sensor
MQTT_WIFI_TOPIC = "sensor/wifi"; # Topik wifi





