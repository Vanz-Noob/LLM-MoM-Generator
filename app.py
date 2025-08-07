# app.py
# Di app.py
from app.video_utils import extract_audio, is_video_file
import streamlit as st
import os
import uuid
import time
import json
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tambahkan direktori 'app' ke sys.path agar bisa mengimpor modul
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# --- Impor konfigurasi dan fungsi utilitas ---
# Muat konfigurasi dari .env
from app.config import Config
# Muat fungsi utilitas
from app.stt_utils import transcribe_with_whisper
from app.video_utils import extract_audio, is_video_file
from app.byteplus_mom_utils import generate_mom_with_byteplus, format_mom_to_text

# --- Setup dan Konfigurasi ---
st.set_page_config(page_title="MoMs Generator", layout="centered")

# Fungsi pembantu untuk memeriksa tipe file
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a', 'flac', 'mp4', 'avi', 'mov', 'mkv', 'webm', 'm4v'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_video_file_local(filename):
    VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'm4v'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in VIDEO_EXTENSIONS

# Fungsi format lokal untuk Whisper (disalin untuk independensi)
def format_whisper_result_local(whisper_result):
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

# --- Fungsi Utama untuk Memproses File ---
def process_file(uploaded_file, progress_bar, status_text):
    """Fungsi utama untuk memproses file audio/video dan menghasilkan MoM."""
    try:
        # 1. Simpan file yang diupload
        original_filename = uploaded_file.name
        unique_id = str(uuid.uuid4())
        base_name = f"{unique_id}_{os.path.splitext(original_filename)[0]}"
        file_extension = os.path.splitext(original_filename)[1]

        # Pastikan direktori upload ada
        upload_folder = Config.UPLOAD_FOLDER
        os.makedirs(upload_folder, exist_ok=True)

        # Simpan file
        file_path = os.path.join(upload_folder, f"{base_name}{file_extension}")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        logger.info(f"File diupload dan disimpan sementara di: {file_path}")
        status_text.text("File berhasil diupload.")

        # 2. Ekstraksi Audio (jika video)
        audio_file_path = file_path
        if is_video_file_local(original_filename):
            status_text.text("Mengekstrak audio dari video...")
            progress_bar.progress(10)
            extracted_audio_filename = f"{base_name}_extracted_audio.wav"
            extracted_audio_path = os.path.join(upload_folder, extracted_audio_filename)
            
            success = extract_audio(file_path, extracted_audio_path)
            
            if success:
                status_text.text("Audio berhasil diekstrak.")
                progress_bar.progress(20)
                audio_file_path = extracted_audio_path
                # Opsional: Hapus file video asli
                # os.remove(file_path)
            else:
                st.error("Gagal mengekstrak audio dari video.")
                return None

        # 3. Transkripsi dengan Whisper
        status_text.text("Melakukan transkripsi dengan Whisper...")
        progress_bar.progress(30)
        whisper_result = transcribe_with_whisper(audio_file_path)
        
        if isinstance(whisper_result, str) and "Terjadi kesalahan" in whisper_result:
            st.error(f"Transkripsi gagal: {whisper_result}")
            return None

        transcription_text = format_whisper_result_local(whisper_result)
        if not transcription_text or "Tidak ada teks" in transcription_text:
            st.error("Transkripsi tidak menghasilkan teks.")
            return None

        status_text.text("Transkripsi selesai.")
        progress_bar.progress(60)
        
        # Simpan transkripsi ke file
        transcript_filename = f"{base_name}_transcription.txt"
        transcript_path = os.path.join(upload_folder, transcript_filename)
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(transcription_text)
        logger.info(f"Transkripsi disimpan ke: {transcript_path}")

        # 4. Buat MoM dengan BytePlus LLM
        status_text.text("Membuat Minutes of Meeting (MoM) dengan BytePlus LLM...")
        progress_bar.progress(70)
        mom_result = generate_mom_with_byteplus(transcription_text)

        if isinstance(mom_result, str) and ("Error" in mom_result or "BYTEPLUS" in mom_result):
            st.error(f"Pembuatan MoM gagal: {mom_result}")
            return None

        if isinstance(mom_result, dict) and "error" in mom_result:
            st.error(f"Pembuatan MoM gagal: {mom_result['error']}")
            return None

        status_text.text("MoM berhasil dibuat.")
        progress_bar.progress(90)

        # Simpan hasil MoM
        mom_json_filename = f"{base_name}_mom_byteplus.json"
        mom_json_path = os.path.join(upload_folder, mom_json_filename)
        with open(mom_json_path, 'w', encoding='utf-8') as f:
            json.dump(mom_result, f, indent=2, ensure_ascii=False)
        logger.info(f"MoM JSON disimpan ke: {mom_json_path}")
        
        mom_text_result = format_mom_to_text(mom_result)
        mom_txt_filename = f"{base_name}_mom_byteplus.txt"
        mom_txt_path = os.path.join(upload_folder, mom_txt_filename)
        with open(mom_txt_path, 'w', encoding='utf-8') as f:
            f.write(mom_text_result)
        logger.info(f"MoM TXT disimpan ke: {mom_txt_path}")
        
        # 5. Selesai
        status_text.text("Semua proses selesai!")
        progress_bar.progress(100)
        
        # Kembalikan path file hasil
        return {
            "transcript_path": transcript_path,
            "transcript_filename": transcript_filename,
            "mom_json_path": mom_json_path,
            "mom_json_filename": mom_json_filename,
            "mom_txt_path": mom_txt_path,
            "mom_txt_filename": mom_txt_filename,
            "transcription_text": transcription_text,
            "mom_text": mom_text_result
        }

    except Exception as e:
        logger.error(f"Terjadi kesalahan dalam process_file: {e}")
        logger.exception("Traceback:")
        st.error(f"Terjadi kesalahan: {str(e)}")
        return None

# --- Halaman Utama (Upload) ---
def main_page():
    st.title("🎙️ MoMs Generator")
    st.subheader("Upload Audio or Video File")

    # Widget upload file di tengah
    uploaded_file = st.file_uploader("Pilih file", type=['mp3', 'wav', 'ogg', 'm4a', 'flac', 'mp4', 'avi', 'mov', 'mkv', 'webm', 'm4v'], label_visibility='collapsed')

    if uploaded_file is not None:
        if allowed_file(uploaded_file.name):
            # Simpan file ke session state untuk digunakan di halaman berikutnya
            st.session_state['uploaded_file'] = uploaded_file
            # Pindah ke halaman proses
            st.session_state['page'] = 'processing'
            st.rerun()
        else:
            st.error("Tipe file tidak didukung.")

# --- Halaman Proses dengan Progress Bar ---
def processing_page():
    st.title("🔄 Processing File...")
    
    # Tampilkan nama file
    uploaded_file = st.session_state.get('uploaded_file')
    if uploaded_file:
        st.write(f"Memproses file: `{uploaded_file.name}`")
    
    # Buat elemen progress bar dan status
    progress_bar = st.progress(0)
    status_text = st.empty() # Placeholder untuk pesan status
    
    # Tombol untuk kembali
    if st.button("Kembali"):
        st.session_state['page'] = 'main'
        st.session_state.pop('uploaded_file', None) # Hapus file dari session
        st.rerun()

    # Jalankan proses ketika halaman dimuat
    # Gunakan st.spinner atau elemen lain untuk menunjukkan aktivitas
    if 'processing_started' not in st.session_state:
        st.session_state['processing_started'] = True
        
        # Jalankan fungsi pemrosesan
        result = process_file(uploaded_file, progress_bar, status_text)
        
        if result:
            # Simpan hasil ke session state
            st.session_state['processing_result'] = result
            # Pindah ke halaman hasil
            st.session_state['page'] = 'results'
            st.rerun()
        else:
            # Jika gagal, tetap di halaman ini atau kembali ke utama
            # Bisa menampilkan pesan error dan tombol coba lagi
            st.error("Proses gagal. Silakan coba lagi.")
            # Opsional: Tambahkan tombol 'Coba Lagi'

# --- Halaman Hasil ---
def results_page():
    st.title("✅ Results")
    
    result = st.session_state.get('processing_result')
    if not result:
        st.warning("Tidak ada hasil untuk ditampilkan.")
        if st.button("Kembali ke Halaman Utama"):
            st.session_state['page'] = 'main'
            st.session_state.pop('processing_result', None)
            st.rerun()
        return

    # Tampilkan Transkripsi
    st.subheader("📄 Transcription")
    st.text_area("Teks Transkripsi", value=result['transcription_text'], height=200, key="transcription_area")
    
    col1, col2 = st.columns(2)
    with col1:
        # Tombol download transkripsi TXT
        with open(result['transcript_path'], "r", encoding='utf-8') as file:
            st.download_button(
                label="💾 Download Transcription (.txt)",
                data=file,
                file_name=result['transcript_filename'],
                mime='text/plain',
            )
    
    # Tampilkan MoM
    st.subheader("📋 Minutes of Meeting (MoM)")
    st.text_area("Teks MoM", value=result['mom_text'], height=300, key="mom_area")
    
    col3, col4 = st.columns(2)
    with col3:
        # Tombol download MoM TXT
        with open(result['mom_txt_path'], "r", encoding='utf-8') as file:
            st.download_button(
                label="💾 Download MoM (.txt)",
                data=file,
                file_name=result['mom_txt_filename'],
                mime='text/plain',
            )
    with col4:
        # Tombol download MoM JSON
        with open(result['mom_json_path'], "r", encoding='utf-8') as file:
            st.download_button(
                label="💾 Download MoM (.json)",
                data=file,
                file_name=result['mom_json_filename'],
                mime='application/json',
            )
    
    # Tombol untuk kembali ke halaman utama
    st.markdown("---")
    if st.button("🏠 Kembali ke Halaman Utama"):
        # Bersihkan session state
        keys_to_delete = [key for key in st.session_state.keys() if key.startswith('processing') or key == 'uploaded_file']
        for key in keys_to_delete:
            st.session_state.pop(key, None)
        st.session_state['page'] = 'main'
        st.rerun()

# --- Routing Aplikasi ---
def main():
    # Inisialisasi session state untuk navigasi
    if 'page' not in st.session_state:
        st.session_state['page'] = 'main'

    # Routing berdasarkan halaman
    if st.session_state['page'] == 'main':
        main_page()
    elif st.session_state['page'] == 'processing':
        processing_page()
    elif st.session_state['page'] == 'results':
        results_page()

if __name__ == "__main__":
    main()
