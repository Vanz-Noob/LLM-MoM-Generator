# app/byteplus_mom_utils.py
import openai
import os
import json
import logging
from app.config import Config

# Konfigurasi logging - pastikan levelnya INFO atau DEBUG untuk detail
logging.basicConfig(level=logging.DEBUG) # Ubah ke DEBUG untuk log lebih detail
logger = logging.getLogger(__name__)

def get_byteplus_client():
    """Membuat dan mengembalikan instance OpenAI client yang dikonfigurasi untuk BytePlus."""
    logger.debug("Mencoba membuat client BytePlus...")
    if not Config.ARK_API_KEY:
        error_msg = "ARK_API_KEY tidak ditemukan di konfigurasi. Pastikan sudah diatur di .env"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    base_url = Config.BYTEPLUS_BASE_URL or 'https://ark.cn-beijing.bytedanceapi.com/api/v3' # Default jika tidak diatur
    logger.info(f"Menggunakan BYTEPLUS_BASE_URL: {base_url}")
    
    client = openai.OpenAI(
        base_url=base_url,
        api_key=Config.ARK_API_KEY, # Library openai akan mencari OS environment variable 'ARK_API_KEY'
    )
    logger.debug("Client BytePlus berhasil dibuat.")
    return client

def create_mom_prompt(transcription_text):
    """
    Membuat prompt yang diberikan ke model LLM BytePlus untuk membuat MoM.
    """
    prompt = f"""
Berdasarkan transkripsi rapat berikut, buatlah Minutes of Meeting (MoM) dalam format JSON yang terstruktur.

Transkripsi:
{transcription_text}

Instruksi:
1. Analisis transkripsi di atas.
2. Identifikasi poin-poin penting, keputusan, dan tindakan yang perlu dilakukan.
3. Hasilkan MoM dalam format JSON yang valid dengan struktur berikut:

{{
  "judul_rapat": "Judul Rapat",
  "tanggal": "Tanggal Rapat (jika disebutkan)",
  "pemimpin_rapat": "Nama Pemimpin Rapat (jika disebutkan)",
  "daftar_hadir": ["Nama Peserta 1", "Nama Peserta 2", "..."],
  "agenda": [
    {{
      "poin_agenda": "Deskripsi singkat agenda",
      "pembahasan": "Ringkasan pembahasan terkait agenda ini",
      "keputusan": "Keputusan yang diambil (jika ada)",
      "tindak_lanjut": [
        {{
          "deskripsi": "Deskripsi tindakan",
          "penanggung_jawab": "Nama Penanggung Jawab",
          "tenggat_waktu": "Tanggal Tenggat Waktu (jika disebutkan)"
        }}
      ]
    }}
  ],
  "kesimpulan": "Ringkasan keseluruhan rapat"
}}

Berikan hanya JSON-nya, tanpa teks tambahan atau markdown.
"""
    return prompt

def generate_mom_with_byteplus(transcription_text):
    """
    Menghasilkan MoM dari teks transkripsi menggunakan LLM BytePlus melalui OpenAI API.
    """
    logger.info("Memulai proses pembuatan MoM dengan BytePlus LLM...")
    
    # 1. Validasi konfigurasi awal
    if not Config.BYTEPLUS_MOM_MODEL:
        error_msg = "BYTEPLUS_MOM_MODEL (Endpoint ID) tidak dikonfigurasi di .env"
        logger.error(error_msg)
        return error_msg

    if not transcription_text or not transcription_text.strip():
        error_msg = "Teks transkripsi kosong atau hanya berisi spasi. Tidak dapat membuat MoM."
        logger.warning(error_msg)
        return error_msg

    prompt = create_mom_prompt(transcription_text)
    logger.debug(f"Prompt yang dikirimkan ke LLM:\n{prompt[:500]}...") # Log sebagian prompt

    try:
        # 2. Dapatkan client yang dikonfigurasi
        client = get_byteplus_client() 
        
        # 3. Siapkan payload untuk API
        model_name = Config.BYTEPLUS_MOM_MODEL
        logger.info(f"Mengirim permintaan ke BytePlus LLM (Model/Endpoint ID: {model_name})...")
        
        # 4. Kirim permintaan ke API
        completion = client.chat.completions.create(
            model=model_name, 
            messages=[
                {"role": "system", "content": "Anda adalah asisten yang ahli dalam membuat Minutes of Meeting (MoM) yang terstruktur dari transkripsi rapat."},
                {"role": "user", "content": prompt}
            ],
            # Tambahkan timeout jika perlu
            # timeout=120 
        )
        logger.debug("Permintaan ke API BytePlus dikirim.")

        # 5. Ekstrak jawaban dari respons
        # Cek apakah ada pilihan (choices) dalam respons
        if not completion.choices:
             error_msg = "Respons dari BytePlus API tidak mengandung 'choices'."
             logger.error(f"{error_msg} Respons lengkap: {completion}")
             return error_msg

        mom_content = completion.choices[0].message.content
        if mom_content is None:
             error_msg = "Konten pesan dalam respons dari BytePlus API adalah None."
             logger.error(error_msg)
             return error_msg
             
        mom_content = mom_content.strip()
        logger.info("Berhasil menerima respons dari BytePlus API.")
        logger.debug(f"Konten respons (potongan awal): {mom_content[:200]}...")

        # 6. Coba parsing JSON untuk memastikan formatnya benar
        if mom_content:
            try:
                mom_json = json.loads(mom_content)
                logger.info("Berhasil mem-parsing MoM ke dalam format JSON.")
                return mom_json
            except json.JSONDecodeError as je:
                error_msg = f"Gagal mem-parsing JSON MoM dari respons BytePlus. Error: {je}. Respons (potongan awal): {mom_content[:500]}..."
                logger.error(error_msg)
                # Opsional: Kembalikan teks mentah jika parsing gagal untuk debugging
                return {"error": error_msg, "raw_response": mom_content[:1000]} # Batasi panjang raw response
        else:
             error_msg = "Respons dari BytePlus API kosong."
             logger.warning(error_msg)
             return error_msg

    # 7. Tangani error dari library openai
    except ValueError as ve: 
         error_msg = f"Konfigurasi error: {str(ve)}"
         logger.error(error_msg)
         return error_msg
    except openai.AuthenticationError as auth_err:
        error_msg = f"BytePlus API key (ARK_API_KEY) tidak valid atau tidak diotorisasi. Detail: {auth_err}"
        logger.error(error_msg)
        return error_msg
    except openai.RateLimitError as rate_err:
        error_msg = f"Quota BytePlus API telah habis atau terkena rate limit. Detail: {rate_err}"
        logger.error(error_msg)
        return error_msg
    except openai.APIConnectionError as conn_err:
         error_msg = f"Terjadi kesalahan koneksi saat menghubungi BytePlus API. Detail: {conn_err}"
         logger.error(error_msg)
         return error_msg
    except openai.APIError as api_err: 
        error_msg = f"Terjadi kesalahan dengan BytePlus API (via OpenAI library). Detail: {api_err}"
        logger.error(error_msg)
        return error_msg
    # 8. Tangani error umum lainnya
    except Exception as e:
        error_msg = f"Terjadi kesalahan umum saat membuat MoM dengan BytePlus: {str(e)}"
        logger.error(error_msg)
        logger.exception("Traceback:") # Ini akan mencetak traceback lengkap
        return error_msg

# Fungsi format_mom_to_text (tetap sama)
def format_mom_to_text(mom_dict):
    """
    Memformat dictionary MoM menjadi teks yang mudah dibaca.
    """
    if not mom_dict or isinstance(mom_dict, str): 
        return mom_dict if isinstance(mom_dict, str) else "Tidak ada data MoM untuk diformat."

    # Cek jika hasilnya adalah error dari generate_mom_with_byteplus
    if isinstance(mom_dict, dict) and "error" in mom_dict:
        return f"Error saat membuat MoM: {mom_dict.get('error', 'Unknown error')}\nRaw Response:\n{mom_dict.get('raw_response', 'N/A')}"

    try:
        lines = []
        lines.append("=" * 50)
        lines.append("MINUTES OF MEETING (MoM)")
        lines.append("=" * 50)
        lines.append(f"Judul Rapat     : {mom_dict.get('judul_rapat', '-')}")
        lines.append(f"Tanggal         : {mom_dict.get('tanggal', '-')}")
        lines.append(f"Pemimpin Rapat  : {mom_dict.get('pemimpin_rapat', '-')}")
        
        daftar_hadir = mom_dict.get('daftar_hadir', [])
        if daftar_hadir:
            lines.append(f"Daftar Hadir    : {', '.join(daftar_hadir)}")
        else:
            lines.append("Daftar Hadir    : -")
        
        lines.append("-" * 30)
        lines.append("Agenda dan Pembahasan:")
        agenda_list = mom_dict.get('agenda', [])
        if agenda_list:
            for i, item in enumerate(agenda_list, 1):
                lines.append(f"  {i}. {item.get('poin_agenda', '-')}")
                lines.append(f"     Pembahasan  : {item.get('pembahasan', '-')}")
                keputusan = item.get('keputusan', '-')
                if keputusan:
                    lines.append(f"     Keputusan   : {keputusan}")
                
                tindak_lanjut = item.get('tindak_lanjut', [])
                if tindak_lanjut:
                    lines.append("     Tindak Lanjut:")
                    for j, tl in enumerate(tindak_lanjut, 1):
                        lines.append(f"       {j}. {tl.get('deskripsi', '-')}")
                        lines.append(f"          Penanggung Jawab: {tl.get('penanggung_jawab', '-')}")
                        tenggat = tl.get('tenggat_waktu', '-')
                        if tenggat:
                            lines.append(f"          Tenggat Waktu   : {tenggat}")
        else:
            lines.append("  (Tidak ada agenda terstruktur ditemukan)")
        
        kesimpulan = mom_dict.get('kesimpulan', '')
        if kesimpulan:
             lines.append("-" * 30)
             lines.append(f"Kesimpulan: {kesimpulan}")

        lines.append("=" * 50)
        
        return "\n".join(lines)
    except Exception as e:
        error_msg = f"Terjadi kesalahan saat memformat MoM ke teks: {str(e)}"
        logger.error(error_msg)
        logger.exception("Traceback:")
        return error_msg
