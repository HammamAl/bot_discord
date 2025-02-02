import paho.mqtt.client as mqtt
from config import *
import asyncio 
import json
import time

class MQTTHandler:
    def __init__(self, bot):
        self.bot = bot
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.sensor_data = {}
        self.wifi_data = {}
        self.ratio = None
        self.relay_on_duration = None
        self.relay_off_duration = None
        self.manual_relay_on_duration = None
        self.relay_status = None
        self.relay_mode = None
        self.ammonia_threshold = None
        self.last_message_time = None  # Menyimpan waktu terakhir penerimaan pesan
        self.is_esp_online = True  # Status ESP32 (Online/Offline)
        self.setup_mqtt()

    def setup_mqtt(self):
        self.client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        self.client.tls_set()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)

        # Jalankan task heartbeat checker
        asyncio.run_coroutine_threadsafe(self.check_esp32_status(), self.bot.loop)


    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("✅ MQTT: Terhubung ke broker!")
            client.subscribe(MQTT_RELAY_STATUS_TOPIC)
            client.subscribe(MQTT_SENSOR_DATA_TOPIC)
            client.subscribe(MQTT_RELAY_SETTING_TOPIC)
            client.subscribe(MQTT_AMMONIA_THRESHOLD_TOPIC)
            client.subscribe(MQTT_HEARTBEAT_TOPIC)
            client.subscribe(MQTT_WIFI_TOPIC)
            client.subscribe(MQTT_RATIO_TOPIC)
        else:
            print(f"❌ MQTT: Gagal terhubung ke broker dengan kode {reason_code}")
    
    async def check_esp32_status(self):
        """Loop untuk memeriksa apakah ESP32 masih terhubung."""
        already_notified_offline = False  # Untuk memastikan notifikasi offline hanya dikirim satu kali

        while True:
            try:
                current_time = time.time()
                if self.last_message_time is None:
                    # Jika tidak ada pesan diterima sejak awal
                    self.is_esp_online = False
                else:
                    # Hitung selisih waktu sejak pesan terakhir
                    time_since_last_message = current_time - self.last_message_time
                    self.is_esp_online = time_since_last_message <= 60

                # Jika ESP32 terdeteksi offline
                if not self.is_esp_online and not already_notified_offline:
                    already_notified_offline = True  # Tandai bahwa notifikasi sudah dikirim
                    channel = self.bot.get_channel(CHANNEL_ID)  # Ambil channel berdasarkan ID
                    if channel:
                        # Kirim notifikasi offline ke channel Discord
                        asyncio.run_coroutine_threadsafe(
                            channel.send(f"-----------------------------\n"
                                f"⚠ **ESP32 tidak terhubung** ke broker MQTT selama lebih dari 60 detik. Pastikan perangkat online."
                            ),
                            self.bot.loop
                        )
                    else:
                        print("⚠ Channel Discord tidak ditemukan!")
                    print("⚠ ESP32 dalam kondisi OFFLINE.")

                # Jika ESP32 kembali online
                elif self.is_esp_online and already_notified_offline:
                    already_notified_offline = False  # Reset flag notifikasi
                    channel = self.bot.get_channel(CHANNEL_ID)
                    if channel:
                        # Kirim notifikasi kembali online ke channel Discord
                        asyncio.run_coroutine_threadsafe(
                            channel.send(
                                "✅ **Sistem kembali online**. Sistem sekarang terhubung dengan broker MQTT. 🚀"
                            ),
                            self.bot.loop
                        )
                    print("✅ ESP32 dalam kondisi ONLINE.")

            except Exception as e:
                print(f"❌ Error saat memeriksa status ESP32: {e}")

            # Tunggu sebelum pengecekan ulang
            await asyncio.sleep(5)

    def on_message(self, client, userdata, msg):
        try:
            self.last_message_time = time.time()
            message = msg.payload.decode("utf-8")
            channel = self.bot.get_channel(CHANNEL_ID)
            print(f"📩 MQTT: Pesan dari topik '{msg.topic}': {message}")
            
            if msg.topic == MQTT_SENSOR_DATA_TOPIC:
                self.sensor_data = json.loads(message)
            elif msg.topic == MQTT_HEARTBEAT_TOPIC:
                if channel:
                    self.relay_alert(channel, message)
                else:
                    print(f"❌ channel tidak ditemukan")
            elif msg.topic == MQTT_WIFI_TOPIC:
                self.wifi_data = json.loads(message)
            elif msg.topic == MQTT_RATIO_TOPIC:
                self.ratio = float(message)
            elif msg.topic == MQTT_AMMONIA_THRESHOLD_TOPIC:
                self.ammonia_threshold = float(message)
            elif msg.topic == MQTT_RELAY_SETTING_TOPIC:
                relay_setting = json.loads(message)
                if relay_setting["command"] == "relay_on":
                    self.relay_on_duration = int(relay_setting["duration"]/1000)
                if relay_setting["command"] == "relay_off":
                    self.relay_off_duration = int(relay_setting["duration"]/1000)
                if relay_setting["command"] == "relay_on_manual":
                    self.manual_relay_on_duration = int(relay_setting["duration"]/1000)
            elif msg.topic == MQTT_RELAY_STATUS_TOPIC:
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
            if self.relay_status == "Relay ON" and self.relay_mode == "AUTO":
                asyncio.run_coroutine_threadsafe(
                    channel.send(f"-----------------------------\n"
                                f"🔔 Peringatan! Amonia Lebih Dari {self.ammonia_threshold} PPM\n"
                                f"• Status { self.relay_status}\n"
                                f"• Relay menyala {self.relay_on_duration} detik"),
                    self.bot.loop)
            if self.relay_status == "Relay OFF" and  self.relay_mode == "AUTO" and affirmation == "OFF":
                asyncio.run_coroutine_threadsafe(
                    channel.send(f"-----------------------------\n"
                                f"🔔 { self.relay_status}, Pendinginan {self.relay_off_duration} detik"),
                    self.bot.loop)
            if self.relay_status == "Relay ON" and  self.relay_mode == "MANUAL" and affirmation == "timer":
                asyncio.run_coroutine_threadsafe(
                    channel.send(f"-----------------------------\n"
                                f"🔔 { self.relay_status}, relay aktif {self.manual_relay_on_duration} detik"),
                    self.bot.loop)
            if self.relay_status == "Relay OFF" and  self.relay_mode == "MANUAL" and affirmation == "timer":
                asyncio.run_coroutine_threadsafe(
                    channel.send(f"-----------------------------\n"
                                f"🔔 { self.relay_status}, relay telah aktif selama {self.manual_relay_on_duration} detik"),
                    self.bot.loop)
            if affirmation == "alive":
                asyncio.run_coroutine_threadsafe(
                    channel.send(f"-----------------------------\n"
                                f"✅ Sistem Pengendali Amonia Telah Siap 🚀\n"
                                f"Silahkan ketik **!guide** untuk informasi lebih lanjut"),
                    self.bot.loop)
        except KeyError as e:
            print(f"❌ MQTT: KeyError pada parsing JSON: {e}")
        except Exception as e:
            print(f"❌ MQTT: Error di relay_alert: {e}")

    def get_sensor_data(self):
        return (
            self.sensor_data.get("suhu"),
            self.sensor_data.get("kelembapan"),
            self.sensor_data.get("amonia"),
        )
    
    def get_wifi_data(self):
        return (
            self.wifi_data.get("ssid"),
            self.wifi_data.get("ipaddress"),
            self.wifi_data.get("wifi_status")
        )

    def get_relay_setting_data(self):
        return (
            self.relay_on_duration,
            self.relay_off_duration,
            self.manual_relay_on_duration
        )

    def get_relay_status_data(self):
        return (
            self.relay_status,
            self.relay_mode
        )
    
    def get_ammonia_threshold(self):
        return self.ammonia_threshold
    
    def get_is_esp_online(self):
        return self.is_esp_online
        
    def get_ratio(self):
        return self.ratio
