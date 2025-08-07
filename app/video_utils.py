# app/video_utils.py
import os
import subprocess
import logging

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Definisi ekstensi file video yang diizinkan ---
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'm4v'}

# --- TAMBAHKAN DEFINISI FUNGSI is_video_file DI SINI ---
def is_video_file(filename):
    """
    Periksa apakah file adalah video berdasarkan ekstensinya.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS
# --- AKHIR TAMBAHAN FUNGSI is_video_file ---

def extract_audio(video_path, audio_output_path):
    """
    Mengekstrak audio dari file video menggunakan ffmpeg.
    Menyimpan audio dalam format WAV.

    :param video_path: Path ke file video input.
    :param audio_output_path: Path untuk menyimpan file audio output (disarankan .wav).
    :return: True jika berhasil, False jika gagal.
    """
    try:
        # Periksa apakah file video ada
        if not os.path.exists(video_path):
            logger.error(f"File video tidak ditemukan: {video_path}")
            return False

        # --- Perintah ffmpeg untuk ekstraksi audio ---
        # -y : overwrite output file jika sudah ada
        # -i : input file
        # -vn : disable video recording (hanya audio)
        # -acodec pcm_s16le : codec audio output (WAV 16-bit PCM - kompatibel baik dengan Whisper)
        # -ar 16000 : sample rate 16kHz (opsional)
        # -ac 1 : mono audio (opsional)
        command = [
            'ffmpeg',
            '-y', # Overwrite output files without asking
            '-i', video_path,
            '-vn', # Disable video
            '-acodec', 'pcm_s16le', # Output codec (WAV)
            '-ar', '16000', # Sample rate (opsional)
            '-ac', '1', # Mono (opsional)
            audio_output_path
        ]

        logger.info(f"Menjalankan ffmpeg command: {' '.join(command)}")
        
        # Jalankan command ffmpeg
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True # Akan melempar CalledProcessError jika command gagal
        )
        
        # Periksa apakah file audio output berhasil dibuat
        if os.path.exists(audio_output_path):
            logger.info(f"Audio berhasil diekstrak ke: {audio_output_path}")
            return True
        else:
            logger.error(f"File audio output tidak ditemukan setelah eksekusi ffmpeg: {audio_output_path}")
            return False

    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg error (CalledProcessError) saat mengekstrak audio: {e}")
        logger.error(f"ffmpeg stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("ffmpeg tidak ditemukan. Pastikan ffmpeg sudah terinstal dan ditambahkan ke PATH sistem.")
        return False
    except Exception as e:
        logger.error(f"Kesalahan umum saat mengekstrak audio: {e}")
        import traceback
        traceback.print_exc()
        return False

# Jika ada bagian __main__ atau fungsi lainnya, biarkan tetap di sini
