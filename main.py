import discord
from discord.ext import commands, tasks
from config import *
from mqtt_handler import MQTTHandler
from data import save_to_csv
from save_data import save_to_gcs
import logging
from datetime import datetime
import shutil
import os

class AmoniaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        
        self.current_mode = "AUTO"
        self.mqtt_handler = None
        
        # Daftar perintah yang tersedia
        self.available_commands = [
            "mode", "manual", "auto", "info", 
            "relay_on", "relay_off", "help", "wifi", "all_data"
        ]

    async def setup_hook(self):
        self.mqtt_handler = MQTTHandler(self)
        self.mqtt_handler.client.loop_start()
        self.monitor_system_task.start()
        self.mqtt_handler.client.on_disconnect = self.on_mqtt_disconnect

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
                "📝 Perintah yang tersedia:\n"
                "• !guide - Menampilkan bantuan\n"
                "• !mode - Cek mode saat ini\n"
                "• !manual - Aktifkan mode manual\n"
                "• !auto - Aktifkan mode otomatis\n"
                "• !info - Tampilkan data sensor\n"
                "• !wifi - Menampilkan info sambungan wifi\n"
                "• !relay_on - Nyalakan relay (mode manual)\n"
                "• !relay_off - Matikan relay (mode manual)\n"
                "• !all_data - mengirim semua data pemantauan sistem\n"
            )
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Anda tidak memiliki izin untuk menggunakan perintah ini!")
        else:
            await ctx.send(f"❌ Terjadi kesalahan: {str(error)}")

    @tasks.loop(seconds=30)
    async def monitor_system_task(self):
        try:
            suhu, kelembapan, amonia = self.mqtt_handler.get_sensor_data()
            if all(x is not None for x in [suhu, kelembapan, amonia]):
                save_to_csv(suhu, kelembapan, amonia)
                save_to_gcs(suhu, kelembapan, amonia)
                print(f"📊 Monitoring: Amonia={amonia}PPM, Suhu={suhu}°C, Kelembapan={kelembapan}%")
                
                if amonia > AMONIA_AMBANG_BATAS:
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
                    f"=====================\n"
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
        help_text = (
            "🤖 *Panduan Penggunaan Bot Pengendali Amonia*\n\n"
            "*Perintah Tersedia:*\n"
            "• !guide - Menampilkan bantuan ini\n"
            "• !mode - Cek mode operasi saat ini\n"
            "• !manual - Aktifkan mode manual\n"
            "• !auto - Aktifkan mode otomatis\n"
            "• !info - Tampilkan data sensor terkini\n"
            "• !wifi - Menampilkan info sambungan wifi\n"
            "• !relay_on - Nyalakan relay (mode manual)\n"
            "• !relay_off - Matikan relay (mode manual)\n"
            "• !all_data - mengirim semua data pemantauan sistem\n\n"
            "*Catatan:*\n"
            "- Perintah relay hanya berfungsi dalam mode manual\n"
            "- Bot akan memberi peringatan otomatis jika level amonia tinggi\n"
            "- Dashboard pemantauan sistem : http://pengendaliamonia.hammamalfarisy.com"
        )
        await ctx.send(help_text)

    @commands.command(name="mode")
    async def check_mode(self, ctx):
        """Cek mode operasi saat ini"""
        try:
            await ctx.send(f"🔧 Mode relay saat ini: *{self.bot.current_mode}*")
        except Exception as e:
            await ctx.send(f"❌ Terjadi kesalahan: {str(e)}")

    @commands.command(name="all_data")
    async def get_csv(self, ctx):
        try:
            await ctx.send(f"Silahkan klik link berikut: https://storage.cloud.google.com/data-sensor-bucket/data_sensor.csv")
        except Exception as e:
            await ctx.send(f"❌ Terjadi kesalahan: {str(e)}")

    @commands.command(name="manual")
    async def mode_manual(self, ctx):
        """Aktifkan mode manual"""
        try:
            self.bot.current_mode = "MANUAL"
            self.bot.mqtt_handler.client.publish(MQTT_RELAY_CONTROL_TOPIC, "MANUAL")
            await ctx.send("✅ Mode relay diubah ke *Manual*.\nGunakan !relay_on atau !relay_off untuk mengontrol relay.")
        except Exception as e:
            await ctx.send(f"❌ Gagal mengubah mode: {str(e)}")

    @commands.command(name="auto")
    async def mode_auto(self, ctx):
        """Aktifkan mode otomatis"""
        try:
            self.bot.current_mode = "AUTO"
            self.bot.mqtt_handler.client.publish(MQTT_RELAY_CONTROL_TOPIC, "AUTO")
            await ctx.send("✅ Mode relay diubah ke *Otomatis*.\nESP32 akan mengatur relay berdasarkan level NH3.")
        except Exception as e:
            await ctx.send(f"❌ Gagal mengubah mode: {str(e)}")

    @commands.command(name="relay_on")
    async def relay_on(self, ctx):
        """Nyalakan relay (mode manual)"""
        try:
            if self.bot.current_mode != "MANUAL":
                await ctx.send("⚠ Relay hanya dapat dihidupkan dalam *Mode Manual*.\nUbah mode dengan perintah !manual.")
                return
            
            self.bot.mqtt_handler.client.publish(MQTT_RELAY_CONTROL_TOPIC, "ON")
            await ctx.send("✅ Relay berhasil dihidupkan (*ON*) melalui perintah manual.")
        except Exception as e:
            await ctx.send(f"❌ Gagal menyalakan relay: {str(e)}")

    @commands.command(name="relay_off")
    async def relay_off(self, ctx):
        """Matikan relay (mode manual)"""
        try:
            if self.bot.current_mode != "MANUAL":
                await ctx.send("⚠ Relay hanya dapat dimatikan dalam *Mode Manual*.\nUbah mode dengan perintah !manual.")
                return
            
            self.bot.mqtt_handler.client.publish(MQTT_RELAY_CONTROL_TOPIC, "OFF")
            await ctx.send("✅ Relay berhasil dimatikan (*OFF*) melalui perintah manual.")
        except Exception as e:
            await ctx.send(f"❌ Gagal mematikan relay: {str(e)}")

    @commands.command(name="info")
    async def info(self, ctx):
        """Tampilkan data sensor terkini"""
        try:
            suhu, kelembapan, amonia = self.bot.mqtt_handler.get_sensor_data()
            if all(x is not None for x in [suhu, kelembapan, amonia]):
                await ctx.send(
                    f"📊 *Data Sistem Pengendali Amonia*\n"
                    f"💩 Amonia: {amonia} PPM\n"
                    f"🌡 Suhu: {suhu}°C\n"
                    f"💧 Kelembapan: {kelembapan}%\n"
                )
            else:
                await ctx.send("⚠ Gagal mendapatkan data sensor! Periksa koneksi.")
        except Exception as e:
            await ctx.send(f"❌ Gagal mengambil data: {str(e)}")
    
    @commands.command(name="wifi")
    async def wifi_info(self, ctx):
        try:
            ssid, ipaddress, wifi_status = self.bot.mqtt_handler.get_wifi_data()
            if all(x is not None for x in [ssid, ipaddress, wifi_status]):
                await ctx.send(
                    f"📶 *Informsi WiFi* 📶\n"
                    f" SSID: {ssid}\n"
                    f" IP Address: {ipaddress}\n"
                    f" Status Wifi: {wifi_status}\n"
                )
            else:
                await ctx.send("⚠ Gagal mendapatkan data wifi! Periksa koneksi.")
        except Exception as e:
            await ctx.send(f"❌ Gagal mengambil data: {str(e)}")

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
