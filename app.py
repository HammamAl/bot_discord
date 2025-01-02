from flask import Flask, jsonify
from flask_cors import CORS
import pandas as pd
from google.cloud import storage  # Library untuk akses GCS
import os
from io import StringIO  # StringIO untuk membaca CSV sebagai file-like object

app = Flask(__name__)
CORS(app)  # Mengizinkan akses API dari sumber lain (CORS)


# Konfigurasi Cloud Storage
BUCKET_NAME = "data-sensor-bucket"  # Ganti dengan nama bucket Google Cloud Storage Anda
CSV_FILE_NAME = "data_sensor.csv"  # Ganti dengan nama file CSV di bucket Anda


def fetch_csv_from_gcs(bucket_name, file_name):
    """
    Mengambil file CSV dari Google Cloud Storage dan mengonversinya menjadi pandas DataFrame.
    """
    try:
        # Inisialisasi Google Cloud Storage Client
        client = storage.Client()

        # Mendapatkan bucket dan file (blob)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_name)

        # Mengunduh file CSV sebagai string
        csv_content = blob.download_as_text()

        # Membaca CSV dengan pandas menggunakan io.StringIO
        data = pd.read_csv(StringIO(csv_content))

        return data

    except FileNotFoundError:
        # Jika file tidak ditemukan
        raise ValueError(f"File '{file_name}' tidak ditemukan di bucket '{bucket_name}'!")
    except pd.errors.EmptyDataError:
        # Jika file CSV kosong
        raise ValueError(f"File '{file_name}' kosong atau tidak mengandung data yang valid!")
    except Exception as e:
        # Jika ada error lain
        raise ValueError(f"Terjadi error saat mengakses file dari GCS: {str(e)}")


@app.route('/api/sensors', methods=['GET'])
def get_sensor_data():
    """
    Endpoint untuk membaca data sensor dari GCS.
    """
    try:
        # Ambil data dari GCS
        data = fetch_csv_from_gcs(BUCKET_NAME, CSV_FILE_NAME)

        # Validasi jika DataFrame kosong
        if data.empty:
            return jsonify({
                'status': 'error',
                'message': 'Data CSV kosong atau tidak ditemukan!'
            }), 404

        # Ubah DataFrame ke format JSON
        result = data.to_dict(orient='records')  # Convert to list of dictionaries
        return jsonify({
            'status': 'success',
            'data': result
        }), 200

    except ValueError as ve:
        # Jika terjadi error selama mengakses data
        return jsonify({
            'status': 'error',
            'message': str(ve)
        }), 500
    except Exception as e:
        # Error tidak terduga
        return jsonify({
            'status': 'error',
            'message': f"Unexpected error: {str(e)}"
        }), 500


@app.route('/api/ping', methods=['GET'])
def ping():
    """
    Endpoint untuk memastikan API berjalan dengan baik.
    """
    return jsonify({
        'status': 'success',
        'message': 'API is working!'
    }), 200


if __name__ == '__main__':
    # Gunakan environment variable PORT, default ke 8080 jika tidak ada
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)  # Pastikan Flask mendengarkan di PORT
