import os
from typing import Final
from dotenv import load_dotenv

# --- Discord Config ---
load_dotenv()
DISCORD_TOKEN: Final[str] = os.getenv("DISCORD_TOKEN") # Discord Token
CHANNEL_ID: Final[int] = int(os.getenv("CHANNEL_ID"))  # ID saluran Discord tempat bot mengirim notifikasi
CHANNEL_NAME: Final[str] = os.getenv("CHANNEL_NAME")  # Nama saluran Discord (opsional, untuk validasi)

# ESP32 Config
AMONIA_AMBANG_BATAS = 30  # Ambang batas Amonia untuk memicu notifikasi otomatis

# MQTT Config
MQTT_BROKER: Final[str] = os.getenv("MQTT_BROKER") # MQTT Broker link
MQTT_PORT: Final[int] = int(os.getenv("MQTT_PORT")) # Port untuk koneksi TLS
MQTT_USER: Final[str] = os.getenv("MQTT_USER") # MQTT User
MQTT_PASSWORD: Final[str] = os.getenv("MQTT_PASSWORD") #MQTT password
MQTT_RELAY_STATUS_TOPIC = "relay/notifications"  # Topik untuk pemberitahuan relay
MQTT_RELAY_CONTROL_TOPIC = "esp32/relay"  # Topik kontrol relay
MQTT_SENSOR_DATA_TOPIC =  "sensor/data" # Topik data sensor
MQTT_RELAY_SETTING_TOPIC = "relay/setting"; # Topik wifi
MQTT_AMMONIA_THRESHOLD_TOPIC = "relay/ammonia"; # Topik ambang batas amonia





