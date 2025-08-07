# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'

    # --- Alibaba Cloud Config (tidak digunakan lagi, bisa dihapus atau dikomentari) ---
    # ALIBABA_ACCESS_KEY_ID = os.environ.get('ALIBABA_ACCESS_KEY_ID')
    # ALIBABA_ACCESS_KEY_SECRET = os.environ.get('ALIBABA_ACCESS_KEY_SECRET')
    # ALIBABA_OSS_ENDPOINT = os.environ.get('ALIBABA_OSS_ENDPOINT')
    # ALIBABA_BUCKET_NAME = os.environ.get('ALIBABA_BUCKET_NAME')
    # ALIBABA_ISI_REGION = os.environ.get('ALIBABA_ISI_REGION') or 'cn-shanghai'

    # --- Whisper Config ---
    WHISPER_MODEL_NAME = os.environ.get('WHISPER_MODEL_NAME') or 'base'

    # --- BytePlus Config (untuk MoM dengan LLM melalui OpenAI API) ---
    ARK_API_KEY = os.environ.get('ARK_API_KEY') # Perhatikan nama variabelnya
    BYTEPLUS_BASE_URL = os.environ.get('BYTEPLUS_BASE_URL') or 'https://ark.cn-beijing.bytedanceapi.com/api/v3' # Default jika tidak diatur
    BYTEPLUS_MOM_MODEL = os.environ.get('BYTEPLUS_MOM_MODEL') # Endpoint ID     


    # --- Validasi Whisper Config ---
    def __init__(self):
        # Tidak perlu validasi Alibaba lagi
        # Tambahkan validasi lain jika diperlukan di masa depan
        pass
