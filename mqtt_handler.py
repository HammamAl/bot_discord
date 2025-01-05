import paho.mqtt.client as mqtt
from config import *
import asyncio 
import json

class MQTTHandler:
    def __init__(self, bot):
        self.bot = bot
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.sensor_data = {}
        self.wifi_data = {}
        self.relay_on_duration = None
        self.relay_off_duration = None
        self.relay_status = None
        self.relay_mode = None
        self.ammonia_threshold = None
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
            client.subscribe(MQTT_RELAY_STATUS_TOPIC)
            client.subscribe(MQTT_SENSOR_DATA_TOPIC)
            client.subscribe(MQTT_RELAY_SETTING_TOPIC)
            client.subscribe(MQTT_AMMONIA_THRESHOLD_TOPIC)
        else:
            print(f"❌ MQTT: Gagal terhubung ke broker dengan kode {reason_code}")
    
    def on_message(self, client, userdata, msg):
        try:
            message = msg.payload.decode("utf-8")
            channel = self.bot.get_channel(CHANNEL_ID)
            print(f"📩 MQTT: Pesan dari topik '{msg.topic}': {message}")

            if msg.topic == MQTT_SENSOR_DATA_TOPIC:
                self.sensor_data = json.loads(message)

            if msg.topic == MQTT_AMMONIA_THRESHOLD_TOPIC:
                self.ammonia_threshold = float(message)

            if msg.topic == MQTT_RELAY_SETTING_TOPIC:
                relay_setting = json.loads(message)
                if relay_setting["command"] == "relay_on":
                    self.relay_on_duration = int(relay_setting["duration"]/1000)
                if relay_setting["command"] == "relay_off":
                    self.relay_off_duration = int(relay_setting["duration"]/1000)  

            if msg.topic == MQTT_RELAY_STATUS_TOPIC:
                relay_data = json.loads(message)
                self.relay_status = relay_data["status"]
                self.relay_mode = relay_data["mode"]
                affirmation = relay_data["affirmation"]
                if channel:
                    self.relay_alert(channel, affirmation)
                else:
                    print(f"❌ channel tidak ditemukan")

        except Exception as e:
            print(f"❌ MQTT: Error saat memproses pesan: {e}")


    def relay_alert(self, channel, affirmation):
        try:    
            if self.relay_status == "Relay ON" and  self.relay_mode == "AUTO":
                asyncio.run_coroutine_threadsafe(
                    channel.send(f"-----------------------------\n"
                                f"🔔 Peringatan! Amonia Lebih Dari {AMONIA_AMBANG_BATAS} PPM\n"
                                f"• Status { self.relay_status}\n"
                                f"• Relay menyala {self.relay_on_duration} detik"),
                    self.bot.loop)
            if self.relay_status == "Relay OFF" and  self.relay_mode == "AUTO" and affirmation == "OFF":
                asyncio.run_coroutine_threadsafe(
                    channel.send(f"-----------------------------\n"
                                f"🔔 { self.relay_status}, Pendinginan {self.relay_off_duration} detik"),
                    self.bot.loop)
        except KeyError as e:
            print(f"❌ MQTT: KeyError pada parsing JSON: {e}")
        except Exception as e:
            print(f"❌ MQTT: Error di relay_alert: {e}")

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

    def get_relay_setting_data(self):
        return (
            self.relay_on_duration,
            self.relay_off_duration
        )

    def get_relay_status_data(self):
        return (
            self.relay_status,
            self.relay_mode
        )
    
    def get_ammonia_threshold(self):
        return (
            self.ammonia_threshold
        )
    