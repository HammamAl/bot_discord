import csv
from datetime import datetime
from google.cloud import storage  # Google Cloud Storage library
import pytz  # Library untuk timezone-aware datetime

# Fungsi untuk menyimpan data ke file CSV dan langsung mengunggahnya ke Google Cloud Storage
def save_to_csv(suhu, kelembapan, amonia, bucket_name="data-sensor-bucket", filename="data_sensor.csv"):
    """
    Menyimpan satu baris data sensor ke file CSV dan langsung mengunggahnya 
    ke Google Cloud Storage secara real-time.
    """
    try:
        # File CSV sementara di lokal
        local_file = "/tmp/" + filename

        # Cek apakah file lokal sudah ada untuk menentukan apakah diperlukan header
        file_exists = False
        try:
            with open(local_file, "r") as _:
                file_exists = True
        except FileNotFoundError:
            file_exists = False

        # Menulis data ke file CSV
        with open(local_file, mode="a", newline="") as file:
            writer = csv.writer(file)
            if not file_exists:  # Tambahkan header jika file belum ada
                writer.writerow(["timestamp", "amonia", "suhu", "kelembapan"])
            
            # Membuat timestamp timezone-aware sesuai timezone lokal atau UTC
            local_timezone = pytz.timezone("Asia/Jakarta")  # Ganti timezone sesuai kebutuhan Anda
            timestamp = datetime.now(local_timezone).strftime("%Y-%m-%d %H:%M:%S")
            
            # Tambahkan data baru dengan timestamp saat ini
            writer.writerow([timestamp, amonia, suhu, kelembapan])

        print(f"✅ Data tersimpan di lokal: {local_file}")

        # Upload file CSV ke Google Cloud Storage
        client = storage.Client()  # Inisialisasi Google Cloud Storage client
        bucket = client.bucket(bucket_name)  # Akses bucket tertentu
        blob = bucket.blob(filename)  # Tentukan nama file di bucket
        blob.upload_from_filename(local_file)  # Unggah file dari lokal ke bucket
        print(f"✅ Data berhasil diunggah ke Google Cloud Storage: {bucket_name}/{filename}")

    except Exception as e:
        print(f"❌ Terjadi kesalahan saat menyimpan atau mengunggah data: {e}")

