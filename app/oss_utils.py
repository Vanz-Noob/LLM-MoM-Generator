# app/oss_utils.py
import oss2
from app.config import Config
import io

def get_oss_bucket():
    """
    Membuat dan mengembalikan instance bucket OSS.
    Ini memastikan autentikasi dan koneksi dibuat hanya saat dibutuhkan.
    """
    if not Config.ALIBABA_ACCESS_KEY_ID or not Config.ALIBABA_ACCESS_KEY_SECRET:
        raise ValueError("ALIBABA_ACCESS_KEY_ID atau ALIBABA_ACCESS_KEY_SECRET tidak ditemukan di konfigurasi.")

    if not Config.ALIBABA_OSS_ENDPOINT or not Config.ALIBABA_BUCKET_NAME:
        raise ValueError("ALIBABA_OSS_ENDPOINT atau ALIBABA_BUCKET_NAME tidak ditemukan di konfigurasi.")

    # Buat objek autentikasi
    auth = oss2.Auth(Config.ALIBABA_ACCESS_KEY_ID, Config.ALIBABA_ACCESS_KEY_SECRET)
    
    # Bangun endpoint URL lengkap
    # Contoh: jika endpoint adalah 'oss-ap-southeast-1.aliyuncs.com'
    # protocol bisa https atau http, disini kita gunakan https
    endpoint_url = f"https://{Config.ALIBABA_OSS_ENDPOINT}"
    
    # Buat instance bucket
    bucket = oss2.Bucket(auth, endpoint_url, Config.ALIBABA_BUCKET_NAME)
    
    return bucket

def upload_file_to_oss(file_storage, object_name):
    """
    Mengunggah file (dari objek FileStorage Flask) ke Alibaba Cloud OSS.

    :param file_storage: Objek FileStorage dari Flask (request.files['file'])
    :param object_name: Nama objek di dalam bucket OSS (nama file yang akan disimpan)
    :return: URL publik dari file yang diunggah
    :raises Exception: Jika terjadi kesalahan saat mengunggah
    """
    try:
        bucket = get_oss_bucket()
        
        # Pastikan pointer file berada di awal
        file_storage.seek(0)
        
        # Unggah file ke OSS
        # file_storage.stream memberikan objek BytesIO/BufferedReader
        # put_object bisa menerima file-like object
        bucket.put_object(object_name, file_storage.stream)
        
        # Bangun URL publik
        # Format: https://<BUCKET_NAME>.<OSS_ENDPOINT>/<OBJECT_NAME>
        public_url = f"https://{Config.ALIBABA_BUCKET_NAME}.{Config.ALIBABA_OSS_ENDPOINT}/{object_name}"
        
        print(f"File '{object_name}' berhasil diunggah ke OSS.")
        return public_url

    except oss2.exceptions.OssError as e:
        # Tangani error spesifik dari OSS
        error_msg = f"Kesalahan OSS saat mengunggah '{object_name}': {e.details}"
        print(error_msg)
        raise Exception(error_msg) from e
    except Exception as e:
        # Tangani error umum
        error_msg = f"Kesalahan umum saat mengunggah '{object_name}' ke OSS: {str(e)}"
        print(error_msg)
        raise Exception(error_msg) from e

# --- Fungsi opsional untuk keperluan lain (misalnya cek keberadaan file) ---
def object_exists_in_oss(object_name):
    """
    Memeriksa apakah objek (file) ada di dalam bucket OSS.

    :param object_name: Nama objek di dalam bucket OSS
    :return: True jika ada, False jika tidak
    """
    try:
        bucket = get_oss_bucket()
        return bucket.object_exists(object_name)
    except oss2.exceptions.NoSuchKey:
        return False
    except Exception as e:
        print(f"Error checking object existence: {e}")
        # Jika tidak yakin, anggap tidak ada
        return False

# --- Contoh cara menggunakan fungsi ini (untuk testing) ---
# if __name__ == '__main__':
#     # Contoh penggunaan (harus ada file 'test.mp3' di direktori ini)
#     from werkzeug.datastructures import FileStorage
#     with open('test.mp3', 'rb') as f:
#         # Buat objek mirip FileStorage
#         class MockFileStorage:
#             def __init__(self, stream):
#                 self.stream = stream
#                 self.filename = 'test.mp3'
#             def seek(self, pos):
#                 self.stream.seek(pos)
#         mock_file = MockFileStorage(f)
#         try:
#             url = upload_file_to_oss(mock_file, 'test_upload.mp3')
#             print(f"Uploaded URL: {url}")
#         except Exception as e:
#             print(f"Upload failed: {e}")
