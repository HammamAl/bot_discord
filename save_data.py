import csv
from datetime import datetime
from google.cloud import storage
import pytz
import os

def save_to_gcs(suhu, kelembapan, amonia, ratio, relay_status, relay_mode, bucket_name="all-data-sensor-bucket"):
    try:
        # Setup waktu
        tz = pytz.timezone("Asia/Jakarta")
        current_time = datetime.now(tz)
        
        # Struktur folder YYYY/MM/data_DD.csv
        folder_path = f"{current_time.strftime('%Y/%m')}"
        filename = f"{folder_path}/data_{current_time.strftime('%d')}.csv"
        timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")

        # Setup GCS
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(filename)

        # Buat folder lokal jika belum ada
        os.makedirs(folder_path, exist_ok=True)
        local_file = f"{folder_path}/data_{current_time.strftime('%d')}.csv"

        # Cek & buat file
        try:
            # Download file jika sudah ada
            blob.download_to_filename(local_file)
            with open(local_file, 'r') as f:
                reader = csv.reader(f)
                existing_data = list(reader)
        except:
            # Buat file baru
            existing_data = [["timestamp", "suhu", "kelembapan", "amonia", "Rs/Ro" , "status relay", "mode relay"]]
            print(f"✅ File baru: {filename}")

        # Tambah data baru
        existing_data.append([timestamp, suhu, kelembapan, amonia, ratio, relay_status, relay_mode])

        # Simpan ke file lokal
        with open(local_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(existing_data)

        # Upload ke GCS
        blob.upload_from_filename(local_file)
        print(f"✅ Tersimpan: {bucket_name}/{filename}")
        print(f"✅ File lokal: {local_file}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")

