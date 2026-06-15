import os

# =============================================================================
# CONFIG.PY — Konfigurasi Web App Prediksi AQI Jakarta
# =============================================================================

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'pkl', 'fitted_rf.pkl')
DB_PATH = os.path.join(BASE_DIR, 'data', 'aqi_history.db')

# --- Flask ---
SECRET_KEY = os.environ.get('SECRET_KEY', 'aqi-jakarta-webapp-secret-key-change-in-prod')
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1')

# --- AQICN API ---
# Ambil token dari environment variable AQICN_TOKEN (dapatkan di aqicn.org/data-platform/token)
AQICN_TOKEN = os.environ.get('AQICN_TOKEN', 'YOUR_AQICN_API_TOKEN')
AQICN_STATION_ID = os.environ.get('AQICN_STATION_ID', 'A531679')
AQICN_URL = f'https://api.waqi.info/feed/{AQICN_STATION_ID}/?token={AQICN_TOKEN}'
AQICN_STATION_NAME = 'KBN Marunda Jakarta Utara'

# --- Model ---
N_LAGS = 8  # Model menggunakan 8 lag values

# --- Email (Gmail SMTP) ---
# Menggunakan environment variable untuk mencegah kebocoran kredensial
EMAIL_ENABLED       = os.environ.get('EMAIL_ENABLED', 'False').lower() in ('true', '1')
EMAIL_HOST          = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT          = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USER          = os.environ.get('EMAIL_USER', 'your-email@gmail.com')
EMAIL_PASSWORD      = os.environ.get('EMAIL_PASSWORD', 'your-gmail-app-password')
EMAIL_SENDER_NAME   = os.environ.get('EMAIL_SENDER_NAME', 'AQI Jakarta')

# --- AQI Categories (ISPU Indonesia — 5 kategori resmi) ---
# Warna: Hijau, Biru, Kuning, Merah, Hitam
AQI_CATEGORIES = [
    (0,   50,  'Baik',              'Good',              '#22c55e'),
    (51,  100, 'Sedang',            'Moderate',          '#3b82f6'),
    (101, 200, 'Tidak Sehat',       'Unhealthy',         '#eab308'),
    (201, 300, 'Sangat Tidak Sehat','Very Unhealthy',    '#ef4444'),
    (301, 999, 'Berbahaya',         'Hazardous',         '#1f2937'),
]

# --- AQI Recommendations ---
AQI_RECOMMENDATIONS = {
    'good': {
        'id': 'Tingkat kualitas udara sangat baik. Tidak memberikan efek negatif terhadap kesehatan manusia, hewan, maupun tumbuhan. Semua aktivitas outdoor aman dilakukan.',
        'en': 'Air quality is very good. No negative effects on human, animal, or plant health. All outdoor activities are safe.',
    },
    'moderate': {
        'id': 'Tingkat kualitas udara masih dapat diterima. Kelompok sensitif (anak-anak, lansia, ibu hamil, penderita asma/jantung) disarankan mengurangi aktivitas outdoor berat yang berkepanjangan.',
        'en': 'Air quality is acceptable. Sensitive groups (children, elderly, pregnant women, asthma/heart patients) should reduce prolonged heavy outdoor activities.',
    },
    'unhealthy': {
        'id': 'Tingkat kualitas udara bersifat merugikan kesehatan. Semua orang disarankan mengurangi aktivitas outdoor. Gunakan masker jika harus keluar rumah. Tutup jendela dan nyalakan air purifier jika tersedia.',
        'en': 'Air quality is unhealthy. Everyone should reduce outdoor activities. Use a mask if going outside. Close windows and use an air purifier if available.',
    },
    'very_unhealthy': {
        'id': 'Tingkat kualitas udara dapat meningkatkan risiko kesehatan pada populasi yang terpapar. Hindari semua aktivitas outdoor. Masker N95 wajib digunakan di luar ruangan. Kelompok sensitif tetap di dalam ruangan.',
        'en': 'Air quality poses increased health risks. Avoid all outdoor activities. N95 mask mandatory outdoors. Sensitive groups must stay indoors.',
    },
    'hazardous': {
        'id': 'BERBAHAYA! Tingkat kualitas udara dapat merugikan kesehatan serius dan perlu penanganan cepat. Tetap di dalam ruangan, tutup semua jendela dan pintu. Hubungi layanan kesehatan jika mengalami sesak napas atau gejala serius.',
        'en': 'HAZARDOUS! Air quality poses serious health risks requiring immediate action. Stay indoors, close all windows and doors. Contact health services if experiencing breathing difficulties.',
    },
}


def get_aqi_category(aqi: float) -> dict:
    """Return category info dict for a given AQI value (ISPU 5-level scale)."""
    keys = ['good', 'moderate', 'unhealthy', 'very_unhealthy', 'hazardous']
    for i, (min_val, max_val, label_id, label_en, color) in enumerate(AQI_CATEGORIES):
        if min_val <= aqi <= max_val:
            rec_key = keys[i]
            return {
                'label_id':          label_id,
                'label_en':          label_en,
                'color':             color,
                'recommendation_id': AQI_RECOMMENDATIONS[rec_key]['id'],
                'recommendation_en': AQI_RECOMMENDATIONS[rec_key]['en'],
            }
    # Fallback: hazardous
    return {
        'label_id':          'Berbahaya',
        'label_en':          'Hazardous',
        'color':             '#1f2937',
        'recommendation_id': AQI_RECOMMENDATIONS['hazardous']['id'],
        'recommendation_en': AQI_RECOMMENDATIONS['hazardous']['en'],
    }
