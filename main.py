import discord
from discord.ext import commands, tasks
from config import *
from mqtt_handler import MQTTHandler
from data import save_to_csv
from save_data import save_to_gcs
import logging
from datetime import datetime
import json
import shutil
import os

class AmoniaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        # Inisialisasi variabel mode default
        self.current_mode = None
        self.relay_on_duration = None
        self.relay_off_duration = None
        self.relay_on_manual_duration = None
        self.mqtt_handler = None
        self.ammonia_threshold = None

        # Daftar perintah yang tersedia
        self.available_commands = [
            "ping", "manual", "auto", "info", "reboot", "guide", "set_relay_on", "set_relay_off",
            "relay_on", "relay_off", "help", "config", "set_timer", "set_ammonia"
        ]

    async def setup_hook(self):
        # Inisialisasi MQTT handler
        self.mqtt_handler = MQTTHandler(self)
        self.mqtt_handler.client.loop_start()
        
        # Menerapkan mode default
        await self.set_default_settings()

        # Memulai monitoring task
        self.monitor_system_task.start()

    async def set_default_settings(self):
        """Mengatur ulang mode default."""
        if self.current_mode is None and self.relay_on_duration is None and self.relay_off_duration is None:
            try:
                # Atur nilai default di dalam bot
                self.current_mode = "AUTO"
                self.relay_on_duration = 30
                self.relay_off_duration = 15
                self.timer_on_duration = 0
                self.ammonia_threshold = 25

                # Kirim pesan MQTT untuk mengatur mode auto ke ESP32
                self.mqtt_handler.client.publish(MQTT_RELAY_CONTROL_TOPIC,  self.current_mode)

                # Kirim pesan MQTT untuk ambang batas ammonia
                data_ammonia = json.dumps({
                    "key" : "begin",
                    "value": self.ammonia_threshold
                    
                })
                self.mqtt_handler.client.publish(MQTT_AMMONIA_THRESHOLD_TOPIC,   data_ammonia)

                # Kirim durasi relay ON ke ESP32
                data_on = json.dumps({
                    "command": "relay_on",
                    "duration": self.relay_on_duration * 1000,  # Dalam milidetik
                    "key" : "begin"
                })
                self.mqtt_handler.client.publish(MQTT_RELAY_SETTING_TOPIC, data_on)

                # Kirim durasi relay OFF ke ESP32
                data_off = json.dumps({
                    "command": "relay_off",
                    "duration": self.relay_off_duration * 1000, # Dalam milidetik
                    "key" : "begin"
                })
                self.mqtt_handler.client.publish(MQTT_RELAY_SETTING_TOPIC, data_off)

                # Kirim durasi relay OFF ke ESP32
                data_timer_on = json.dumps({
                    "command": "timer_on",
                    "duration": self.timer_on_duration,
                    "key" : "begin"
                })
                self.mqtt_handler.client.publish(MQTT_RELAY_SETTING_TOPIC, data_timer_on)
                print("✅ Sistem berhasil diatur ke mode default: AUTO dengan durasi auto : ON=30s, OFF=30s dan manual : ON=0")

            except Exception as e:
                print(f"❌ Gagal mengatur sistem ke mode default: {e}")
        else:
            print("⚠ Sistem sudah diatur. Melewati inisialisasi ulang mode default.")

    # MQTT Handler
    async def on_mqtt_disconnect(self, client, userdata, rc):
        logging.warning("MQTT Disconnected. Mencoba reconnect...")
        await self.mqtt_handler.connect()
    
    # Menangani pesan yang tidak valid
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            command_used = ctx.message.content.split()[0][1:]  # Mengambil perintah yang digunakan
            await ctx.send(
                f"❌ Perintah {command_used} tidak tersedia!\n\n"
                "📝 Untuk melihat perintah yang tersedia silahkan ketik '!guide'\n"
            )
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Anda tidak memiliki izin untuk menggunakan perintah ini!")
        else:
            await ctx.send(f"❌ Terjadi kesalahan: {str(error)}")

    @tasks.loop(seconds=30)
    async def monitor_system_task(self):
        try:
            is_esp_online = self.mqtt_handler.get_is_esp_online()
            relay_status, relay_mode = self.mqtt_handler.get_relay_status_data()
            suhu, kelembapan, amonia = self.mqtt_handler.get_sensor_data()
            voltage_mems = self.mqtt_handler.get_voltage_mems()
            if all(x is not None for x in [suhu, kelembapan, amonia]):
                if is_esp_online:
                    save_to_csv(suhu, kelembapan, amonia)
                    save_to_gcs(suhu, kelembapan, amonia, voltage_mems, relay_status, relay_mode)
                    print(f"📊 Monitoring: Amonia={amonia}PPM, Suhu={suhu}°C, Kelembapan={kelembapan}%, Rasio={ratio}")
                
                if amonia > self.ammonia_threshold:
                    await self.send_notification(amonia, suhu, kelembapan)
            else:
                print("⚠ Tidak Dapat Membaca Data Sensor.")
        except Exception as e:
            print(f"❌ Error dalam monitor_system_task: {e}")

    async def send_notification(self, amonia, suhu, kelembapan):
        try:
            channel = self.get_channel(CHANNEL_ID)
            if channel:
                await channel.send(
                    f"-----------------------------\n"
                    f"🚨 Peringatan! Amonia tinggi terdeteksi!\n"
                    f"💩 Amonia: {amonia} PPM\n"
                    f"🌡 Suhu: {suhu}°C\n"
                    f"💧 Kelembapan: {kelembapan}%\n"
                    f"✅ Pastikan kondisi ruangan tetap aman."
                )
        except Exception as e:
            print(f"❌ Error dalam send_notification: {e}")

    async def setup(self):
        await self.add_cog(CommandsCog(self))

class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="guide")
    async def help_command(self, ctx):
        """Menampilkan bantuan penggunaan bot"""
        help_text = "🤖 *Panduan Penggunaan Bot Pengendali Amonia*\n\n"
        help_text += "*Perintah Tersedia:*\n"
        for command in self.bot.commands:
            if command.name != "!help" and command.help != "Shows this message":
                help_text += f"• !{command.name}  -  {command.help}\n"
        help_text += (
            "\n*Catatan:*\n- Perintah !relay_on dan !relay_off hanya berfungsi dalam mode manual\n"
            "- Bot akan memberi peringatan otomatis jika level amonia tinggi dalam mode otomatis\n"
            "- **!set_ammonia** mengatur ambang batas amonia saat mode otomatis\n"
            "- **!set_relay_on** dan **!set_relay_off** hanya mengatur ON/OFF relay saat mode otomatis\n"
            "- **!set_relay_on**, **!set_relay_off**, **!set_ammonia** hanya dapat digunakan dalam mode manual\n"
            "- Dashboard pemantauan sistem: http://pengendaliamonia.hammamalfarisy.com"
        )
        await ctx.send(help_text)

    @commands.command(name="manual")
    async def mode_manual(self, ctx):
        """Aktifkan mode manual"""
        try:
            self.bot.current_mode = "MANUAL"
            self.bot.mqtt_handler.client.publish(MQTT_RELAY_CONTROL_TOPIC, self.bot.current_mode )
            await ctx.send("✅ Mode relay diubah ke **Manual**.\n"
                           "• Setting untuk mode **Otomatis** diperbolehkan.\n"
                           "• Gunakan **!relay_on** atau **!relay_off** untuk mengontrol relay.\n"
                           "• Gunakan **!set_timer** untuk kontrol relay dengan timer."
                           )
        except Exception as e:
            await ctx.send(f"❌ Gagal mengubah mode: {str(e)}")

    @commands.command(name="auto")
    async def mode_auto(self, ctx):
        """Aktifkan mode otomatis"""
        try:
            self.bot.current_mode = "AUTO"
            self.bot.mqtt_handler.client.publish(MQTT_RELAY_CONTROL_TOPIC, self.bot.current_mode)
            await ctx.send("✅ Mode relay diubah ke **Otomatis**.\nESP32 akan mengatur relay berdasarkan level NH3.")
        except Exception as e:
            await ctx.send(f"❌ Gagal mengubah mode: {str(e)}")

    @commands.command(name="relay_on")
    async def relay_on(self, ctx):
        """Nyalakan relay (mode manual)"""
        try:
            if self.bot.current_mode != "MANUAL":
                await ctx.send("⚠ Relay hanya dapat dihidupkan dalam **Mode Manual**.\nUbah mode dengan perintah !manual.")
                return
            
            self.bot.mqtt_handler.client.publish(MQTT_RELAY_CONTROL_TOPIC, "ON")
            await ctx.send("✅ Relay berhasil dihidupkan (**ON**) melalui perintah manual.")
        except Exception as e:
            await ctx.send(f"❌ Gagal menyalakan relay: {str(e)}")

    @commands.command(name="relay_off")
    async def relay_off(self, ctx):
        """Matikan relay (mode manual)"""
        try:
            if self.bot.current_mode != "MANUAL":
                await ctx.send("⚠ Relay hanya dapat dimatikan dalam **Mode Manual**.\nUbah mode dengan perintah !manual.")
                return
            
            self.bot.mqtt_handler.client.publish(MQTT_RELAY_CONTROL_TOPIC, "OFF")
            await ctx.send("✅ Relay berhasil dimatikan (**OFF**) melalui perintah manual.")
        except Exception as e:
            await ctx.send(f"❌ Gagal mematikan relay: {str(e)}")

    @commands.command(name="timer_on")
    async def timer_on(self, ctx):
        """Menyalakan relay dalam mode timer"""
        try:
            if self.bot.current_mode != "MANUAL":
                await ctx.send("⚠ Relay hanya dapat dihidupkan dalam **Mode Manual**.\nUbah mode dengan perintah **!manual**.")
                return
            if self.timer_on_duration == 0:
                await ctx.send(f"⚠ Durasi Timer {self.timer_on_duration}\nsilahkan setting timer terlebih dahulu\ndengan perintah **!set_timer**.")
            
            self.bot.mqtt_handler.client.publish(MQTT_RELAY_CONTROL_TOPIC, "TIMER")
            await ctx.send("✅ Timer berhasil aktif lewat perintah manual.")
        except Exception as e:
            await ctx.send(f"❌ Gagal menyalakan relay: {str(e)}")

    @commands.command(name="info")
    async def info(self, ctx):
        """Tampilkan data sensor terkini"""
        try:
            is_esp_online = self.bot.mqtt_handler.get_is_esp_online()
            if not is_esp_online:
                await ctx.send("❌ ESP32 Offline, data sensor tidak dapat diproses")
                return

            suhu, kelembapan, amonia = self.bot.mqtt_handler.get_sensor_data()
            if all(x is not None for x in [suhu, kelembapan, amonia]):
                await ctx.send(
                    f"-----------------------------\n"
                    f"📊 *Data Sistem Pengendali Amonia*\n"
                    f"💩 Amonia: {amonia} PPM\n"
                    f"🌡 Suhu: {suhu}°C\n"
                    f"💧 Kelembapan: {kelembapan}%\n"
                )
            else:
                await ctx.send("⚠ Gagal mendapatkan data sensor! Periksa koneksi.")
        except Exception as e:
            await ctx.send(f"❌ Gagal mengambil data: {str(e)}")

    
    @commands.command(name="set_relay_on")
    async def set_relay_on(self, ctx, duration: int):
        """contoh : !set_relay_on  <detik>"""
        try:
            if self.bot.current_mode != "MANUAL":
                await ctx.send("⚠ set_relay_on hanya dapat digunakan dalam **Mode Manual**.\nUbah mode dengan perintah !manual.")
                return

            if duration < 5 or duration > 1800:  # Membatasi durasi antara 5 detik dan 30 menit
                await ctx.send("⚠ Durasi harus antara 5 - 1800 detik (5 detik - 30 menit).")
                return

            self.bot.relay_on_duration = duration
            data_json = json.dumps({
                            "command" : "relay_on",
                            "duration" : str(duration*1000),
                            "key" : "running"
                        })
            self.bot.mqtt_handler.client.publish(MQTT_RELAY_SETTING_TOPIC, data_json)
            await ctx.send(f"✅ Durasi nyala relay berhasil diatur menjadi **{duration}** detik.")
        except Exception as e:
            await ctx.send(f"❌ Gagal setting relay: {str(e)}")

    @commands.command(name="set_relay_off")
    async def set_relay_off(self, ctx, duration: int):
        """contoh : !set_relay_off  <detik>"""
        try:
            if self.bot.current_mode != "MANUAL":
                await ctx.send("⚠ !set_relay_off hanya dapat digunakan dalam ***Mode Manual***.\nUbah mode dengan perintah !manual.")
                return
            
            if duration < 5 or duration > 1800:  # Membatasi durasi antara 5 detik dan 30 menit
                await ctx.send("⚠ Durasi harus antara 5 - 1800 detik (5 detik - 30 menit).")
                return

            self.bot.relay_off_duration = duration
            data_json = json.dumps({
                            "command" : "relay_off",
                            "duration" : str(duration*1000),
                            "key" : "running"
                        })
            self.bot.mqtt_handler.client.publish(MQTT_RELAY_SETTING_TOPIC, data_json)
            await ctx.send(f"✅ Durasi cooldown relay berhasil diatur menjadi **{duration}** detik.")
        except Exception as e:
            await ctx.send(f"❌ Gagal setting relay: {str(e)}")

    @commands.command(name="set_timer")
    async def set_timer(self, ctx, duration: int):
        """contoh : !set_timer <detik>"""
        try:
            if self.bot.current_mode != "MANUAL":
                await ctx.send("⚠ set_timer hanya dapat digunakan dalam **Mode Manual**.")
                return

            # Update nilai timer di bot
            self.bot.timer_on_duration = duration * 1000  # Simpan dalam milidetik

            # Kirim setting timer ke ESP32
            data_json = json.dumps({
                "command": "timer_on",
                "duration": duration * 1000,  # Konversi ke milidetik
                "key": "running"
            })

            # Publish ke MQTT
            self.bot.mqtt_handler.client.publish(MQTT_RELAY_SETTING_TOPIC, data_json)

            await ctx.send(f"✅ Timer diatur: relay akan ON selama **{duration}** detik.\n"
                        f"• Gunakan **!timer_on** untuk mengaktifkan relay dengan timer.")

        except Exception as e:
            print(f"Error dalam set_timer: {e}")  # Debug print
            await ctx.send(f"❌ Gagal setting timer: {str(e)}")

    @commands.command(name="set_ammonia")
    async def set_ammonia(self, ctx, value: float):
        """contoh : !set_ammonia  <PPM>"""
        try:
            if self.bot.current_mode != "MANUAL":
                await ctx.send("⚠ set_ammonia hanya dapat digunakan dalam **Mode Manual**.\nUbah mode dengan perintah !manual.")
                return
            
            if value < 10 or value > 300:  # Membatasi setting ambang batas amonia 
                await ctx.send("⚠ Nilai harus antara 10 - 300 PPM.")
                return

            self.bot.ammonia_threshold = value
            data_json = json.dumps({
                            "key" : "running",
                            "value" : value
                        })
            self.bot.mqtt_handler.client.publish(MQTT_AMMONIA_THRESHOLD_TOPIC, data_json)
            await ctx.send(f"✅ Ambang batas menjadi amonia **{value}** PPM.")
        except Exception as e:
            await ctx.send(f"❌ Gagal setting ambang batas ammonia: {str(e)}")

    @commands.command(name="config")
    async def system_info(self, ctx):
        """Menampilkan informasi sistem"""
        try:
            is_esp_online = self.bot.mqtt_handler.get_is_esp_online()
            ammonia_threshold = self.bot.mqtt_handler.get_ammonia_threshold()
            relay_status, relay_mode = self.bot.mqtt_handler.get_relay_status_data()
            relay_on_duration, relay_off_duration, manual_relay_duration = self.bot.mqtt_handler.get_relay_setting_data()
            ssid, ipaddress, wifi_status = self.bot.mqtt_handler.get_wifi_data()
            wifi_connection_status = "**Connected**" if is_esp_online else "Not Connected"
            await ctx.send(f"🛠️ *Informasi Sistem Pengendali Amonia* 🛠️\n"
                           f"• SSID: **{ssid}**\n"
                           f"• IP Address: **{ipaddress}**\n"
                           f"• Status Wifi: **{wifi_connection_status}**\n"
                           f"• Status relay saat ini: **{relay_status}**\n"
                           f"• Mode relay saat ini: **{relay_mode}**\n"
                           f"• Ambang batas amonia (otomatis): **{ammonia_threshold}** PPM\n"
                           f"• Relay ON (otomatis): **{relay_on_duration}** detik\n"
                           f"• Relay OFF (otomatis): **{relay_off_duration}** detik\n"
                           f"• Relay ON (manual): **{manual_relay_duration}** detik\n")
        except Exception as e:
            await ctx.send(f"❌ Terjadi kesalahan: {str(e)}")

    @commands.command(name="ping")
    async def is_esp_online(self, ctx):
        """Cek apakah ESP32 online"""
        try:
            is_esp_online = self.bot.mqtt_handler.get_is_esp_online()
            self.bot.mqtt_handler.client.publish(MQTT_ISONLINE_TOPIC, "online")
            send_to_channel = "✅ Online" if is_esp_online else "❌ Offline"
            await ctx.send(f"Status ESP32 : **{send_to_channel}**,")
        except Exception as e:
            await ctx.send(f"❌ Gagal mengubah mode: {str(e)}")
    
    @commands.command(name="reboot")
    async def esp_restart(self, ctx):
        """Restart ESP32"""
        try:
            is_esp_online = self.bot.mqtt_handler.get_is_esp_online()
            if not is_esp_online:
                await ctx.send("❌ ESP32 Offline, data sensor tidak dapat diproses")
                return
            self.bot.mqtt_handler.client.publish(MQTT_RESTART_TOPIC, "restart")
            await ctx.send(f"✅ ESP32 akan direstart dalam **5** detik")
        except Exception as e:
            await ctx.send(f"❌ Gagal mengubah mode: {str(e)}")


def main():
    bot = AmoniaBot()

    @bot.event
    async def on_ready():
        print(f"✅ Bot telah login sebagai {bot.user.name}")
        await bot.setup()

    bot.run(DISCORD_TOKEN)

logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def backup_csv():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    shutil.copy2(
        'data.csv',
        f'backup/data_{timestamp}.csv'
    )

def set_google_application_credentials():
    # Path ke file JSON kredensial akun layanan
    credentials_path = "/home/alfarisihammam/bot-discord-446507-82e5fe39653e.json"

    # Pastikan file JSON kredensial ada
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"File kredensial tidak ditemukan: {credentials_path}")

    if not os.access(credentials_path, os.R_OK):
        raise PermissionError("Tidak bisa membaca credentials")

    # Tetapkan variabel lingkungan GOOGLE_APPLICATION_CREDENTIALS
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    print(f"✅ Variabel GOOGLE_APPLICATION_CREDENTIALS telah diset ke: {credentials_path}")

if __name__ == "__main__":
    try:
        set_google_application_credentials()
        print("🎉 Berhasil mengatur variabel lingkungan! Anda siap menggunakan Google Cloud Storage.")
    except Exception as e:
        print(f"❌ Terjadi kesalahan: {e}")
    main()

