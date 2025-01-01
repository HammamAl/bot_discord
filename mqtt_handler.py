import paho.mqtt.client as mqtt
from config import *
import json

class MQTTHandler:
    def __init__(self, bot):
        self.bot = bot
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.sensor_data = {}
        self.wifi_data = {}
        self.setup_mqtt()

    def setup_mqtt(self):
        self.client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        self.client.tls_set()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("✅ MQTT: Terhubung ke broker!")
            client.subscribe(MQTT_TOPIC_RELAY_STATUS)
            client.subscribe(MQTT_SENSOR_DATA_TOPIC)
            client.subscribe(MQTT_WIFI_TOPIC)
        else:
            print(f"❌ MQTT: Gagal terhubung ke broker dengan kode {reason_code}")
    
    def on_message(self, client, userdata, msg):
            try:
                message = msg.payload.decode("utf-8")
                print(f"📩 MQTT: Pesan dari topik '{msg.topic}': {message}")

                if msg.topic == MQTT_SENSOR_DATA_TOPIC:
                    self.sensor_data = json.loads(message)
                
                if msg.topic == MQTT_WIFI_TOPIC:
                    self.wifi_data = json.loads(message)
                    
                channel = self.bot.get_channel(CHANNEL_ID)
                if channel and msg.topic == MQTT_TOPIC_RELAY_STATUS:
                    self.relay_alert(channel, message)
                    
            except Exception as e:
                print(f"❌ MQTT: Error saat memproses pesan: {e}")

    async def relay_alert(self, channel, message):
            if message == "Relay ON":
                await channel.send(f"🔔 Peringatan! Amonia Lebih Dari {AMONIA_AMBANG_BATAS} PPM, Status {message}")
            else:
                await channel.send(f"🔔 {message}, Pendinginan 30 detik")

    def get_sensor_data(self):
        return (
            self.sensor_data.get("suhu"),
            self.sensor_data.get("kelembapan"),
            self.sensor_data.get("amonia")
        )
    
    def get_wifi_data(self):
        return (
            self.sensor_data.get("ssid"),
            self.sensor_data.get("ipaddress"),
            self.sensor_data.get("wifi_status")
        )


