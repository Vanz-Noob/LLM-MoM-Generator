# run.py
from app import create_app

# Buat instance aplikasi Flask
app = create_app()

# Cek apakah ini file yang dijalankan langsung
if __name__ == '__main__':
    # Jalankan aplikasi dalam mode debug
    # Ini akan memulai server pengembangan bawaan Flask
    print("Memulai aplikasi Flask...")
    app.run(debug=True)