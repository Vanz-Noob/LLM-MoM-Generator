# app/routes.py
import os
import uuid
import base64
import json
import time
import threading
import logging
from flask import Blueprint, render_template, request, redirect, url_for, current_app, Response, send_file
from werkzeug.utils import secure_filename

# --- Impor fungsi dari modul lain ---
# Pastikan fungsi-fungsi ini tidak menggunakan `current_app` secara langsung di dalam proses background
# atau jika digunakan, sudah diperbaiki.
from app.stt_utils import transcribe_with_whisper
from app.video_utils import extract_audio
from app.byteplus_mom_utils import generate_mom_with_byteplus, format_mom_to_text

# Setup logger untuk file ini
logger = logging.getLogger(__name__)

# --- Konfigurasi File ---
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a', 'flac'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'm4v'}
ALLOWED_EXTENSIONS = ALLOWED_AUDIO_EXTENSIONS.union(ALLOWED_VIDEO_EXTENSIONS)

# --- Fungsi Pembantu ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def generate_unique_filename(original_filename):
    unique_str = str(uuid.uuid4())
    encoded = base64.urlsafe_b64encode(unique_str.encode()).decode('utf-8')
    file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    if file_ext:
        return f"{encoded}.{file_ext}"
    else:
        return encoded

# --- Dictionary untuk menyimpan status proses (Untuk demo, gunakan mem cache. Untuk produksi, gunakan Redis/DB) ---
processing_status = {}

# --- Fungsi Latar Belakang untuk Memproses File ---
# --- PERUBAHAN: Terima upload_folder dan base_url (jika diperlukan di masa depan) sebagai argumen ---
def background_process(file_path, unique_id, original_filename, upload_folder):
    """Fungsi yang dijalankan di thread terpisah untuk memproses file."""
    global processing_status
    try:
        # Gunakan upload_folder yang diteruskan, bukan current_app.config['UPLOAD_FOLDER']
        UPLOAD_FOLDER = upload_folder

        processing_status[unique_id] = {"status": "started", "message": "Proses dimulai...", "progress": 0}

        # --- 1. Ekstraksi Audio (jika video) ---
        audio_file_path = file_path
        if is_video_file(original_filename):
            processing_status[unique_id] = {"status": "processing", "message": "Mengekstrak audio dari video...", "progress": 10}
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            extracted_audio_filename = f"{base_name}_extracted_audio.wav"
            # --- GUNAKAN UPLOAD_FOLDER YANG DITERUSKAN ---
            extracted_audio_path = os.path.join(UPLOAD_FOLDER, extracted_audio_filename)
            
            success = extract_audio(file_path, extracted_audio_path)
            
            if success:
                processing_status[unique_id]["message"] = "Audio berhasil diekstrak."
                processing_status[unique_id]["progress"] = 20
                audio_file_path = extracted_audio_path
                # Opsional: Hapus file video asli setelah ekstraksi
                # os.remove(file_path)
            else:
                processing_status[unique_id]["status"] = "error"
                processing_status[unique_id]["message"] = "Gagal mengekstrak audio dari video."
                processing_status[unique_id]["progress"] = 0
                return # Hentikan proses

        # --- 2. Transkripsi dengan Whisper ---
        processing_status[unique_id] = {"status": "processing", "message": "Melakukan transkripsi dengan Whisper...", "progress": 30}
        whisper_result = transcribe_with_whisper(audio_file_path)
        
        # Fungsi format_whisper_result perlu didefinisikan atau diimpor
        # Kita definisikan di sini untuk memastikan kemandirian
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

        if isinstance(whisper_result, str) and "Terjadi kesalahan" in whisper_result:
            processing_status[unique_id]["status"] = "error"
            processing_status[unique_id]["message"] = f"Transkripsi gagal: {whisper_result}"
            processing_status[unique_id]["progress"] = 0
            return

        transcription_text = format_whisper_result_local(whisper_result) # Gunakan fungsi lokal
        if not transcription_text or "Tidak ada teks" in transcription_text:
             processing_status[unique_id]["status"] = "error"
             processing_status[unique_id]["message"] = "Transkripsi tidak menghasilkan teks."
             processing_status[unique_id]["progress"] = 0
             return

        processing_status[unique_id]["message"] = "Transkripsi selesai."
        processing_status[unique_id]["progress"] = 60
        
        # Simpan transkripsi ke file
        base_name_final = os.path.splitext(os.path.basename(audio_file_path))[0]
        transcript_filename = f"{base_name_final}_transcription.txt"
        # --- GUNAKAN UPLOAD_FOLDER YANG DITERUSKAN ---
        transcript_path = os.path.join(UPLOAD_FOLDER, transcript_filename)
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(transcription_text)
        processing_status[unique_id]["transcript_file"] = transcript_filename
        logger.info(f"Transkripsi disimpan ke: {transcript_path}")

        # --- 3. Buat MoM dengan BytePlus LLM ---
        processing_status[unique_id] = {"status": "processing", "message": "Membuat Minutes of Meeting (MoM) dengan BytePlus LLM...", "progress": 70}
        mom_result = generate_mom_with_byteplus(transcription_text)

        # --- PERIKSA JUGA JIKA generate_mom_with_byteplus MENGAKSES current_app ---
        # Jika iya, Anda perlu memperbaikinya juga dengan cara yang sama.
        # Misalnya, oper konfigurasi yang dibutuhkan ke fungsi tersebut.

        if isinstance(mom_result, str) and ("Error" in mom_result or "BYTEPLUS" in mom_result):
            processing_status[unique_id]["status"] = "error"
            processing_status[unique_id]["message"] = f"Pembuatan MoM gagal: {mom_result}"
            processing_status[unique_id]["progress"] = 0
            return # Hentikan proses

        # Jika mom_result adalah dict error dari byteplus_mom_utils
        if isinstance(mom_result, dict) and "error" in mom_result:
             processing_status[unique_id]["status"] = "error"
             processing_status[unique_id]["message"] = f"Pembuatan MoM gagal: {mom_result['error']}"
             processing_status[unique_id]["progress"] = 0
             return

        processing_status[unique_id]["message"] = "MoM berhasil dibuat."
        processing_status[unique_id]["progress"] = 90

        # Simpan hasil MoM
        mom_json_filename = f"{base_name_final}_mom_byteplus.json"
        # --- GUNAKAN UPLOAD_FOLDER YANG DITERUSKAN ---
        mom_json_path = os.path.join(UPLOAD_FOLDER, mom_json_filename)
        with open(mom_json_path, 'w', encoding='utf-8') as f:
            json.dump(mom_result, f, indent=2, ensure_ascii=False)
        logger.info(f"MoM JSON disimpan ke: {mom_json_path}")
        
        mom_text_result = format_mom_to_text(mom_result) # Pastikan fungsi ini tidak akses current_app
        mom_txt_filename = f"{base_name_final}_mom_byteplus.txt"
        # --- GUNAKAN UPLOAD_FOLDER YANG DITERUSKAN ---
        mom_txt_path = os.path.join(UPLOAD_FOLDER, mom_txt_filename)
        with open(mom_txt_path, 'w', encoding='utf-8') as f:
            f.write(mom_text_result)
        logger.info(f"MoM TXT disimpan ke: {mom_txt_path}")
        
        processing_status[unique_id]["mom_json_file"] = mom_json_filename
        processing_status[unique_id]["mom_txt_file"] = mom_txt_filename
        
        # --- 4. Selesai ---
        processing_status[unique_id] = {
            "status": "completed", 
            "message": "Semua proses selesai!", 
            "progress": 100,
            "transcript_file": transcript_filename,
            "mom_json_file": mom_json_filename,
            "mom_txt_file": mom_txt_filename
        }
        logger.info(f"Proses untuk {unique_id} selesai.")

    except Exception as e:
        error_msg = f"Terjadi kesalahan tak terduga di background_process: {str(e)}"
        logger.error(error_msg)
        logger.exception("Traceback:")
        processing_status[unique_id] = {"status": "error", "message": error_msg, "progress": 0}
    finally:
        # Opsional: Bersihkan file sementara jika perlu
        pass

# --- Inisialisasi Routes ---
def init_routes(app):
    bp = Blueprint('main', __name__)

    @bp.route('/')
    def index():
        return render_template('index.html')

    @bp.route('/process_file', methods=['POST'])
    def process_file():
        """Route untuk menangani upload file dan memulai proses latar belakang."""
        global processing_status
        if 'file' not in request.files:
            return "No file part in the request", 400
        
        file = request.files['file']
        if file.filename == '':
            return "No file selected", 400

        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            unique_id = str(uuid.uuid4())
            
            processing_status[unique_id] = {"status": "starting", "message": "Memulai proses...", "progress": 0}

            unique_filename = generate_unique_filename(original_filename)
            # --- PERUBAHAN: Dapatkan UPLOAD_FOLDER dari current_app SEBELUM memulai thread ---
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, unique_filename)
            
            file.save(file_path)
            logger.info(f"File diupload dan disimpan sementara di: {file_path}")

            # --- PERUBAHAN: Oper upload_folder sebagai argumen ---
            thread = threading.Thread(target=background_process, args=(file_path, unique_id, original_filename, upload_folder))
            thread.start()
            
            return redirect(url_for('main.mom_result', process_id=unique_id))
        else:
            return "File type not allowed", 400

    @bp.route('/mom_result')
    def mom_result():
        """Route untuk menampilkan halaman hasil dengan progress bar."""
        process_id = request.args.get('process_id')
        if not process_id or process_id not in processing_status:
            return "Invalid or expired process ID", 404
        return render_template('mom_result.html', process_id=process_id)

    @bp.route('/stream_status/<process_id>')
    def stream_status(process_id):
        """Route untuk streaming status proses menggunakan Server-Sent Events (SSE)."""
        def generate():
            global processing_status
            last_status = None
            while True:
                if process_id in processing_status:
                    current_status = processing_status[process_id]
                    if current_status != last_status:
                        # Gunakan text/plain untuk kesederhanaan, atau text/event-stream untuk MIME resmi
                        yield f"data: {json.dumps(current_status)}\n\n" 
                        last_status = current_status
                    
                    if current_status.get("status") in ["completed", "error"]:
                        # Opsional: Hapus status setelah selesai untuk demo
                        # del processing_status[process_id] 
                        break
                else:
                    yield f"data: {json.dumps({'status': 'error', 'message': 'Process ID not found or expired.', 'progress': 0})}\n\n"
                    break
                time.sleep(1) # Tunggu 1 detik sebelum cek lagi

        # --- PERUBAHAN: Gunakan mimetype text/event-stream untuk SSE ---
        return Response(generate(), mimetype='text/event-stream')

    # --- PERUBAHAN: Fungsi download_file dengan penanganan error yang lebih baik ---
    @bp.route('/download/<filename>')
    def download_file(filename):
        try:
            # Lindungi dari path traversal
            safe_filename = os.path.basename(filename)
            logger.info(f"Memulai proses download untuk file: {safe_filename}")

            # Pastikan UPLOAD_FOLDER diambil dengan benar dari current_app (dalam context request)
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            logger.debug(f"Menggunakan folder upload: {upload_folder}")

            # Bangun path lengkap file
            file_path = os.path.join(upload_folder, safe_filename)
            logger.debug(f"Path lengkap file yang akan diunduh: {file_path}")

            # Periksa apakah file benar-benar ada
            if os.path.exists(file_path):
                logger.info(f"File ditemukan, mengirim file: {file_path}")
                # Kirim file untuk diunduh
                return send_file(file_path, as_attachment=True)
            else:
                logger.warning(f"File tidak ditemukan di path: {file_path}")
                # Kembalikan error 404 jika file tidak ada
                return "File not found", 404

        except PermissionError as pe:
            logger.error(f"Izin akses ditolak saat mencoba membaca file {file_path}: {pe}")
            return "Akses ke file ditolak", 500
        except FileNotFoundError as fnfe:
            logger.error(f"File tidak ditemukan meskipun dicek keberadaannya: {file_path}. Error: {fnfe}")
            return "File tidak ditemukan", 500
        except Exception as e:
            # Tangkap error umum lainnya
            logger.error(f"Terjadi kesalahan tak terduga saat mendownload file {filename}: {e}")
            logger.exception("Traceback:") # Ini akan mencetak traceback lengkap
            # Kembalikan error 500 generik atau pesan yang lebih ramah
            return "Terjadi kesalahan saat memproses permintaan download.", 500

    app.register_blueprint(bp)
