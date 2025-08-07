# app/stt_utils.py
import whisper
import os
import time

# --- Konfigurasi Whisper ---
# Pilih model Whisper. Pilihan umum:
# 'tiny', 'base', 'small', 'medium', 'large'
# 'tiny' paling cepat tapi akurasi terendah
# 'large' paling akurat tapi paling lambat dan butuh resource besar
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "base") # Gunakan 'base' sebagai default

# Muat model Whisper sekali saja saat aplikasi dimulai untuk efisiensi
# Ini akan memakan waktu beberapa detik hingga menit tergantung model dan hardware
print(f"Memuat model Whisper '{WHISPER_MODEL_NAME}'...")
MODEL = whisper.load_model(WHISPER_MODEL_NAME)
print(f"Model Whisper '{WHISPER_MODEL_NAME}' berhasil dimuat.")

def transcribe_with_whisper(audio_file_path, task="transcribe"):
    """
    Melakukan transkripsi audio menggunakan model Whisper.

    :param audio_file_path: Path lengkap ke file audio lokal.
    :param task: Tugas yang dilakukan ('transcribe' atau 'translate').
                     'translate' menerjemahkan ke teks Inggris.
    :return: Dictionary hasil transkripsi dari Whisper, atau string error.
    """
    try:
        print(f"Memulai transkripsi file: {audio_file_path} menggunakan model '{WHISPER_MODEL_NAME}'...")
        start_time = time.time()

        # --- Jalankan model Whisper ---
        # `task` bisa 'transcribe' (default) atau 'translate'
        result = MODEL.transcribe(audio_file_path, task=task, verbose=False)

        end_time = time.time()
        duration = end_time - start_time
        print(f"Transkripsi selesai dalam {duration:.2f} detik.")

        return result

    except Exception as e:
        error_msg = f"Terjadi kesalahan saat transkripsi dengan Whisper: {str(e)}"
        print(error_msg)
        return error_msg

def format_whisper_result(whisper_result):
    """
    Memformat hasil dari model Whisper menjadi teks dengan timestamp.

    :param whisper_result: Dictionary hasil dari `model.transcribe()`.
    :return: String teks yang diformat.
    """
    if not whisper_result or isinstance(whisper_result, str): # Jika error
        return whisper_result if isinstance(whisper_result, str) else "Tidak ada hasil transkripsi."

    formatted_text = ""
    segments = whisper_result.get("segments", [])
    
    if segments:
        for segment in segments:
            # Waktu dalam detik dari Whisper
            start_sec = segment.get("start", 0)
            end_sec = segment.get("end", 0)
            text = segment.get("text", "").strip()

            # Hanya tambahkan baris jika ada teks
            if text:
                formatted_text += f"[{start_sec:.2f} - {end_sec:.2f}] {text}\n"
        return formatted_text
    else:
        # Jika tidak ada segments, gunakan teks penuh
        full_text = whisper_result.get("text", "").strip()
        if full_text:
             return full_text
        else:
             return "Tidak ada teks yang dikenali dalam audio."
