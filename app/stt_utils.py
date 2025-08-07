# app/stt_utils.py
import whisper
import torch # Tambahkan import torch
import os
import time

# --- Konfigurasi Whisper ---
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "base")

# --- Deteksi Perangkat ---
# Periksa apakah CUDA (GPU) tersedia
if torch.cuda.is_available():
    DEVICE = "cuda"
    print(f"GPU CUDA terdeteksi: {torch.cuda.get_device_name(0)}")
elif torch.backends.mps.is_available(): # Untuk Mac dengan chip Apple Silicon
    DEVICE = "mps"
    print("MPS (Metal Performance Shaders) terdeteksi.")
else:
    DEVICE = "cpu"
    print("Tidak ada GPU yang terdeteksi, menggunakan CPU.")

# --- Muat Model Whisper ---
print(f"Memuat model Whisper '{WHISPER_MODEL_NAME}' ke perangkat '{DEVICE}'...")
# Muat model dan pindahkan ke perangkat yang terdeteksi
MODEL = whisper.load_model(WHISPER_MODEL_NAME).to(DEVICE)
print(f"Model Whisper '{WHISPER_MODEL_NAME}' berhasil dimuat di '{DEVICE}'.")

def transcribe_with_whisper(audio_file_path, task="transcribe"):
    """
    Melakukan transkripsi audio menggunakan model Whisper.
    Model akan berjalan di GPU jika tersedia.

    :param audio_file_path: Path lengkap ke file audio lokal.
    :param task: Tugas yang dilakukan ('transcribe' atau 'translate').
    :return: Dictionary hasil transkripsi dari Whisper, atau string error.
    """
    try:
        print(f"Memulai transkripsi file: {audio_file_path} menggunakan model '{WHISPER_MODEL_NAME}' di '{DEVICE}'...")
        start_time = time.time()

        # --- Jalankan model Whisper ---
        # HAPUS device=DEVICE dari baris di bawah ini
        result = MODEL.transcribe(audio_file_path, task=task, verbose=False)
        # -----------------------------

        end_time = time.time()
        duration = end_time - start_time
        print(f"Transkripsi selesai dalam {duration:.2f} detik di '{DEVICE}'.")

        return result

    except Exception as e:
        error_msg = f"Terjadi kesalahan saat transkripsi dengan Whisper di '{DEVICE}': {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return error_msg

def format_whisper_result(whisper_result):
    """
    Memformat hasil dari model Whisper menjadi teks dengan timestamp.

    :param whisper_result: Dictionary hasil dari `model.transcribe()`.
    :return: String teks yang diformat.
    """
    if not whisper_result or isinstance(whisper_result, str):
        return whisper_result if isinstance(whisper_result, str) else "Tidak ada hasil transkripsi."

    formatted_text = ""
    segments = whisper_result.get("segments", [])
    
    if segments:
        for segment in segments:
            start_sec = segment.get("start", 0)
            end_sec = segment.get("end", 0)
            text = segment.get("text", "").strip()

            if text:
                formatted_text += f"[{start_sec:.2f} - {end_sec:.2f}] {text}\n"
        return formatted_text
    else:
        full_text = whisper_result.get("text", "").strip()
        if full_text:
             return full_text
        else:
             return "Tidak ada teks yang dikenali dalam audio."
