import os
from typing import Final
from dotenv import load_dotenv

# --- Discord Config ---
load_dotenv()
DISCORD_TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1320978354417041491  # ID saluran Discord tempat bot mengirim notifikasi
CHANNEL_NAME = "general"  # Nama saluran Discord (opsional, untuk validasi)

# ESP32 Config
AMONIA_AMBANG_BATAS = 30  # Ambang batas Amonia untuk memicu notifikasi otomatis

# MQTT Config
MQTT_BROKER = "499b37cd93464a848333539b957a57ef.s1.eu.hivemq.cloud"
MQTT_PORT = 8883  # Port untuk koneksi TLS
MQTT_USER = "percobaan1"
MQTT_PASSWORD = "Percobaan2024"
MQTT_TOPIC_RELAY_STATUS = "relay/notifications"  # Topik untuk pemberitahuan relay
MQTT_RELAY_CONTROL_TOPIC = "esp32/relay"  # Topik kontrol relay
MQTT_SENSOR_DATA_TOPIC =  "sensor/data" # Topik data sensor
MQTT_WIFI_TOPIC = "sensor/wifi"; # Topik wifi

