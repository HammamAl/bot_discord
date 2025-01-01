import csv
from datetime import datetime

# Fungsi untuk menyimpan data ke file CSV
def save_to_csv(suhu, kelembapan, amonia, filename="data_suhu.csv"):
    """Menyimpan data suhu dan kelembapan ke file CSV"""
    # Buat header kolom jika file belum ada
    file_exists = False
    try:
        with open(filename, "r"):
            file_exists = True
    except FileNotFoundError:
        file_exists = False

    # Membuka file CSV untuk menulis (append mode)
    with open(filename, mode="a", newline="") as file:
        writer = csv.writer(file)

        # Tulis header jika file baru
        if not file_exists:
            writer.writerow(["timestamp","amonia", "suhu", "kelembapan"])

        # Tulis data suhu dan kelembapan ke baris baru
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([timestamp, amonia, suhu, kelembapan])
        print(f"✅ Data berhasil disimpan ke {filename}")

