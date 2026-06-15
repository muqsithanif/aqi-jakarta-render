import os
import json
import pickle
import sqlite3
import smtplib
import requests
import numpy as np
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, render_template, g
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from config import (
    SECRET_KEY, DEBUG,
    MODEL_PATH, DB_PATH,
    AQICN_URL, AQICN_STATION_NAME,
    N_LAGS,
    get_aqi_category,
)

# =============================================================================
# APP INIT
# =============================================================================

app = Flask(__name__)
app.secret_key = SECRET_KEY

# =============================================================================
# MODEL LOADING
# =============================================================================

def load_model():
    bundle = pickle.load(open(MODEL_PATH, 'rb'))
    return {
        'model':      bundle['model'],
        'scaler':     bundle['scaler'],      # None for RF
        'lag_cols':   bundle['lag_cols'],    # ['lag_1', ..., 'lag_8']
        'k_final':    bundle['k_final'],     # 8
        'model_name': bundle['model_name'],  # 'Random Forest'
        'params':     bundle['params'],
    }

try:
    MODEL_BUNDLE = load_model()
    print(f"[OK] Model loaded: {MODEL_BUNDLE['model_name']} (k={MODEL_BUNDLE['k_final']})")
except Exception as e:
    MODEL_BUNDLE = None
    print(f"[ERROR] Failed to load model: {e}")

# =============================================================================
# DATABASE
# =============================================================================

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS aqi_daily (
            date       TEXT PRIMARY KEY,
            aqi        REAL,
            source     TEXT,
            station    TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS predictions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_date TEXT,
            predicted_aqi   REAL,
            input_data      TEXT,
            source          TEXT,
            created_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS subscribers (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT UNIQUE,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS notification_log (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            type    TEXT,
            date    TEXT,
            sent_at TEXT
        );
    """)
    conn.commit()
    conn.close()
    print("[OK] Database initialised")

# =============================================================================
# HELPERS
# =============================================================================

def now_wib() -> str:
    """Return current datetime string in WIB (UTC+7)."""
    wib = timezone(timedelta(hours=7))
    return datetime.now(wib).strftime('%Y-%m-%d %H:%M:%S')

def today_wib() -> str:
    wib = timezone(timedelta(hours=7))
    return datetime.now(wib).strftime('%Y-%m-%d')

def predict_aqi(lag_values: list) -> float:
    """Run model prediction from a list of N_LAGS AQI values (most recent first)."""
    if MODEL_BUNDLE is None:
        raise RuntimeError("Model not loaded")
    X = np.array(lag_values[:N_LAGS], dtype=float).reshape(1, -1)
    return float(MODEL_BUNDLE['model'].predict(X)[0])

def get_last_n_aqi(n: int = N_LAGS) -> list:
    """Return last n AQI values from DB, most recent first."""
    db = get_db()
    rows = db.execute(
        "SELECT aqi FROM aqi_daily ORDER BY date DESC LIMIT ?", (n,)
    ).fetchall()
    return [row['aqi'] for row in rows]

def log_prediction(prediction_date: str, predicted_aqi: float,
                   input_data: list, source: str):
    db = get_db()
    db.execute(
        "INSERT INTO predictions (prediction_date, predicted_aqi, input_data, source, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (prediction_date, predicted_aqi, json.dumps(input_data), source, now_wib())
    )
    db.commit()

# =============================================================================
# ROUTES
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html')


# ---------------------------------------------------------------------------
# GET /api/current-aqi
# Fetch AQI hari ini dari AQICN, simpan ke DB, return JSON
# ---------------------------------------------------------------------------
@app.route('/api/current-aqi')
def current_aqi():
    try:
        resp = requests.get(AQICN_URL, timeout=8)
        resp.raise_for_status()
        data = resp.json()

        if data.get('status') != 'ok':
            return jsonify({'error': 'API returned non-ok status', 'detail': data}), 502

        aqi_data = data['data']
        aqi_val   = float(aqi_data['aqi'])
        dom_pol   = aqi_data.get('dominentpol', 'pm25')
        city_name = aqi_data.get('city', {}).get('name', AQICN_STATION_NAME)
        time_str  = aqi_data.get('time', {}).get('s', today_wib())
        date_str  = time_str[:10]          # 'YYYY-MM-DD'
        iaqi      = aqi_data.get('iaqi', {})

        # Upsert ke DB
        db = get_db()
        db.execute(
            "INSERT OR REPLACE INTO aqi_daily (date, aqi, source, station, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (date_str, aqi_val, 'aqicn_api', city_name, now_wib())
        )
        db.commit()

        category = get_aqi_category(aqi_val)

        return jsonify({
            'date':        date_str,
            'aqi':         aqi_val,
            'dominant_pol': dom_pol,
            'station':     city_name,
            'iaqi':        {k: v['v'] for k, v in iaqi.items()},
            'category':    category,
            'updated_at':  time_str,
        })

    except requests.exceptions.Timeout:
        return jsonify({'error': 'API request timed out'}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'API request failed: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/predict-auto
# Prediksi AQI besok dari 8 hari terakhir di DB
# ---------------------------------------------------------------------------
@app.route('/api/predict-auto', methods=['POST'])
def predict_auto():
    try:
        lag_values = get_last_n_aqi(N_LAGS)

        if len(lag_values) < N_LAGS:
            return jsonify({
                'error': 'insufficient_data',
                'message': f'Dibutuhkan minimal {N_LAGS} hari data. Tersedia: {len(lag_values)} hari.',
                'message_en': f'Need at least {N_LAGS} days of data. Available: {len(lag_values)} days.',
                'available': len(lag_values),
                'required':  N_LAGS,
            }), 422

        predicted = predict_aqi(lag_values)
        category  = get_aqi_category(predicted)

        # Ambil data 8 hari dari DB untuk grafik
        db = get_db()
        rows = db.execute(
            "SELECT date, aqi FROM aqi_daily ORDER BY date DESC LIMIT ?", (N_LAGS,)
        ).fetchall()
        history = [{'date': r['date'], 'aqi': r['aqi']} for r in reversed(rows)]

        # Tanggal prediksi = hari setelah data terbaru
        latest_date = rows[0]['date'] if rows else today_wib()
        next_date = (datetime.strptime(latest_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

        log_prediction(next_date, predicted, lag_values, 'auto')

        return jsonify({
            'prediction_date': next_date,
            'predicted_aqi':   round(predicted, 2),
            'category':        category,
            'lag_values':      lag_values,
            'history':         history,
        })

    except RuntimeError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/predict-csv
# Prediksi dari CSV upload (kolom: date + AQI)
# ---------------------------------------------------------------------------
@app.route('/api/predict-csv', methods=['POST'])
def predict_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'File harus berformat CSV'}), 400

    try:
        df = pd.read_csv(file)
        df.columns = df.columns.str.strip().str.lower()

        # Detect date column
        date_col = next((c for c in df.columns if c in ('date', 'tanggal', 'datetime', 'time')), None)
        if date_col is None:
            return jsonify({'error': 'Kolom tanggal tidak ditemukan. Gunakan: date, tanggal, datetime, atau time'}), 422

        # Detect AQI column
        aqi_col = next((c for c in df.columns if c in ('aqi', 'ispu', 'pm25')), None)
        if aqi_col is None:
            return jsonify({'error': 'Kolom AQI tidak ditemukan. Gunakan: aqi, ispu, atau pm25'}), 422

        df = df[[date_col, aqi_col]].copy()
        df.columns = ['date', 'aqi']
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna().sort_values('date')

        if len(df) < N_LAGS:
            return jsonify({
                'error': 'insufficient_data',
                'message': f'CSV membutuhkan minimal {N_LAGS} baris data. Ditemukan: {len(df)} baris.',
                'message_en': f'CSV needs at least {N_LAGS} rows. Found: {len(df)} rows.',
            }), 422

        # Ambil 8 terbaru, lag_1 = paling baru
        last8 = df.tail(N_LAGS)['aqi'].tolist()
        lag_values = list(reversed(last8))   # most recent first

        predicted = predict_aqi(lag_values)
        category  = get_aqi_category(predicted)

        history = [
            {'date': row['date'].strftime('%Y-%m-%d'), 'aqi': row['aqi']}
            for _, row in df.tail(N_LAGS).iterrows()
        ]

        latest_date = df['date'].iloc[-1]
        next_date   = (latest_date + timedelta(days=1)).strftime('%Y-%m-%d')

        log_prediction(next_date, predicted, lag_values, 'csv_upload')

        return jsonify({
            'prediction_date': next_date,
            'predicted_aqi':   round(predicted, 2),
            'category':        category,
            'lag_values':      lag_values,
            'history':         history,
            'filename':        file.filename,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# GET /api/daily-data
# Semua data harian dari DB (desc)
# ---------------------------------------------------------------------------
@app.route('/api/daily-data')
def daily_data():
    try:
        db = get_db()
        rows = db.execute(
            "SELECT date, aqi, source, station, created_at "
            "FROM aqi_daily ORDER BY date DESC"
        ).fetchall()

        records = []
        for r in rows:
            cat = get_aqi_category(r['aqi'])
            records.append({
                'date':       r['date'],
                'aqi':        r['aqi'],
                'source':     r['source'],
                'station':    r['station'],
                'created_at': r['created_at'],
                'category':   cat,
            })

        return jsonify({'count': len(records), 'data': records})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/preload-csv
# Upload historical CSV ke DB (bulk insert)
# ---------------------------------------------------------------------------
@app.route('/api/preload-csv', methods=['POST'])
def preload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'File harus berformat CSV'}), 400

    try:
        df = pd.read_csv(file)
        df.columns = df.columns.str.strip().str.lower()

        date_col = next((c for c in df.columns if c in ('date', 'tanggal', 'datetime', 'time')), None)
        aqi_col  = next((c for c in df.columns if c in ('aqi', 'ispu', 'pm25')), None)

        if date_col is None:
            return jsonify({'error': 'Kolom tanggal tidak ditemukan'}), 422
        if aqi_col is None:
            return jsonify({'error': 'Kolom AQI tidak ditemukan'}), 422

        df = df[[date_col, aqi_col]].copy()
        df.columns = ['date', 'aqi']
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna().sort_values('date')

        if len(df) == 0:
            return jsonify({'error': 'Tidak ada data valid dalam CSV'}), 422

        db = get_db()
        inserted = 0
        skipped  = 0
        for _, row in df.iterrows():
            date_str = row['date'].strftime('%Y-%m-%d')
            try:
                db.execute(
                    "INSERT OR IGNORE INTO aqi_daily (date, aqi, source, station, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (date_str, float(row['aqi']), 'preload', 'CSV Upload', now_wib())
                )
                if db.execute("SELECT changes()").fetchone()[0] > 0:
                    inserted += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1

        db.commit()

        return jsonify({
            'success':  True,
            'inserted': inserted,
            'skipped':  skipped,
            'total':    len(df),
            'message':  f'{inserted} data berhasil disimpan, {skipped} dilewati (sudah ada).',
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# EMAIL
# =============================================================================

def build_email_html(aqi_val: float, category: dict, date_str: str,
                     station: str, is_welcome: bool = False,
                     pred_aqi: float = None, pred_date: str = None,
                     pred_category: dict = None) -> str:
    """Build HTML email body for AQI notification, including tomorrow's prediction."""
    color    = category['color']
    label    = category['label_id']
    rec      = category['recommendation_id']
    title    = 'Selamat datang di AQI Jakarta!' if is_welcome else f'Info AQI Jakarta — {date_str}'
    greeting = (
        'Terima kasih telah mendaftar notifikasi AQI Jakarta.<br>'
        'Berikut kondisi udara Jakarta hari ini dan prediksi besok:'
        if is_welcome else
        'Berikut informasi kualitas udara Jakarta hari ini dan prediksi besok:'
    )

    # Build prediction block
    if pred_aqi is not None and pred_category is not None:
        pc     = pred_category['color']
        pl     = pred_category['label_id']
        pr     = pred_category['recommendation_id']
        pred_block = f"""
        <!-- Prediction tomorrow -->
        <tr>
          <td style="padding:0 32px 20px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="background:#f8f9fc;border:1px solid #e2e8f0;
                           border-radius:8px;padding:16px 20px;text-align:center;">
                  <p style="margin:0 0 10px;font-size:11px;font-weight:700;
                             color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;">
                    Prediksi Besok &mdash; {pred_date or ''}
                  </p>
                  <div style="display:inline-flex;align-items:center;gap:14px;">
                    <div style="background:{pc}18;border:2px solid {pc};
                                border-radius:8px;padding:12px 24px;text-align:center;">
                      <div style="font-size:36px;font-weight:800;color:{pc};
                                  line-height:1;letter-spacing:-.02em;">
                        {int(round(pred_aqi))}
                      </div>
                      <div style="font-size:11px;font-weight:700;color:{pc};
                                  margin-top:4px;letter-spacing:.05em;text-transform:uppercase;">
                        {pl}
                      </div>
                    </div>
                  </div>
                  <div style="margin-top:12px;border-left:3px solid {pc};
                              background:#fff;border-radius:0 5px 5px 0;
                              padding:10px 14px;text-align:left;">
                    <p style="margin:0 0 3px;font-size:10px;font-weight:700;
                               color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;">
                      Rekomendasi untuk Besok
                    </p>
                    <p style="margin:0;font-size:12px;color:#334155;line-height:1.6;">
                      {pr}
                    </p>
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>"""
    else:
        pred_block = ''

    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f0f5ff;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f5ff;padding:32px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:8px;overflow:hidden;
                    box-shadow:0 2px 12px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#1a365d,#2b579a);
                     padding:28px 32px;text-align:center;">
            <p style="margin:0;font-size:11px;color:rgba(255,255,255,.6);
                      letter-spacing:.08em;text-transform:uppercase;">
              Prediksi AQI Jakarta
            </p>
            <h1 style="margin:6px 0 0;font-size:20px;font-weight:700;color:#fff;">
              {title}
            </h1>
          </td>
        </tr>

        <!-- Greeting -->
        <tr>
          <td style="padding:24px 32px 0;text-align:center;">
            <p style="margin:0;font-size:14px;color:#64748b;line-height:1.6;">
              {greeting}
            </p>
          </td>
        </tr>

        <!-- AQI Today -->
        <tr>
          <td style="padding:16px 32px 0;text-align:center;">
            <p style="margin:0 0 10px;font-size:11px;font-weight:700;
                      color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;">
              AQI Hari Ini &mdash; {date_str}
            </p>
            <div style="display:inline-block;background:{color}18;
                        border:2px solid {color};border-radius:8px;
                        padding:20px 40px;margin-bottom:6px;">
              <div style="font-size:56px;font-weight:800;color:{color};
                          line-height:1;letter-spacing:-.02em;">
                {int(round(aqi_val))}
              </div>
              <div style="font-size:12px;font-weight:700;color:{color};
                          margin-top:6px;letter-spacing:.06em;text-transform:uppercase;">
                {label}
              </div>
            </div>
            <p style="margin:4px 0 0;font-size:12px;color:#94a3b8;">
              {station}
            </p>
          </td>
        </tr>

        <!-- Recommendation today -->
        <tr>
          <td style="padding:16px 32px 20px;">
            <div style="border-left:3px solid {color};background:#f8f9fc;
                        border-radius:0 6px 6px 0;padding:14px 16px;">
              <p style="margin:0 0 4px;font-size:11px;font-weight:700;
                        color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;">
                Rekomendasi Hari Ini
              </p>
              <p style="margin:0;font-size:13px;color:#334155;line-height:1.65;">
                {rec}
              </p>
            </div>
          </td>
        </tr>

        {pred_block}

        <!-- AQI Scale -->
        <tr>
          <td style="padding:0 32px 20px;">
            <p style="margin:0 0 8px;font-size:11px;color:#94a3b8;
                      text-transform:uppercase;letter-spacing:.06em;">
              Skala AQI
            </p>
            <table width="100%" cellpadding="0" cellspacing="2">
              <tr>
                {''.join(f'<td style="background:{c};height:8px;border-radius:3px;"></td>'
                         for c in ['#22c55e','#3b82f6','#eab308','#ef4444','#1f2937'])}
              </tr>
              <tr>
                {''.join(f'<td style="font-size:9px;color:#94a3b8;padding-top:3px;text-align:center;">{lbl}</td>'
                         for lbl in ['Baik','Sedang','Tidak Sehat','Sangat Tidak Sehat','Berbahaya'])}
              </tr>
              <tr>
                <td style="font-size:9px;color:#94a3b8;">0</td>
                <td style="font-size:9px;color:#94a3b8;text-align:center;">51</td>
                <td style="font-size:9px;color:#94a3b8;text-align:center;">101</td>
                <td style="font-size:9px;color:#94a3b8;text-align:center;">201</td>
                <td style="font-size:9px;color:#94a3b8;text-align:right;">301+</td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8f9fc;padding:16px 32px;
                     border-top:1px solid #e2e8f0;text-align:center;">
            <p style="margin:0;font-size:11px;color:#94a3b8;line-height:1.6;">
              Email ini dikirim otomatis dari <strong>AQI Jakarta</strong>.<br>
              Sumber data: AQICN · Stasiun {station}<br>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def send_email(to_email: str, subject: str, html_body: str) -> tuple:
    """Send an email via Gmail SMTP. Returns (success: bool, message: str)."""
    if not config.EMAIL_ENABLED:
        return False, 'Email belum dikonfigurasi (EMAIL_ENABLED=False di config.py)'

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f"{config.EMAIL_SENDER_NAME} <{config.EMAIL_USER}>"
        msg['To']      = to_email
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        with smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
            smtp.sendmail(config.EMAIL_USER, to_email, msg.as_string())

        return True, 'OK'

    except smtplib.SMTPAuthenticationError:
        return False, 'Autentikasi Gmail gagal. Pastikan App Password sudah benar.'
    except smtplib.SMTPException as e:
        return False, f'SMTP error: {str(e)}'
    except Exception as e:
        return False, str(e)


def fetch_current_aqi_data() -> dict | None:
    """Fetch AQI from AQICN API, return processed dict or None."""
    try:
        resp = requests.get(AQICN_URL, timeout=8)
        data = resp.json()
        if data.get('status') != 'ok':
            return None
        d        = data['data']
        aqi_val  = float(d['aqi'])
        time_str = d.get('time', {}).get('s', today_wib())
        date_str = time_str[:10]

        # Upsert ke DB agar data terbaru tersedia untuk prediksi
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR REPLACE INTO aqi_daily (date, aqi, source, station, created_at) VALUES (?,?,?,?,?)",
            (date_str, aqi_val, 'aqicn_api',
             d.get('city', {}).get('name', AQICN_STATION_NAME), now_wib())
        )
        conn.commit()
        conn.close()

        return {
            'aqi':      aqi_val,
            'date':     date_str,
            'station':  d.get('city', {}).get('name', AQICN_STATION_NAME),
            'category': get_aqi_category(aqi_val),
        }
    except Exception:
        return None


def fetch_prediction_data() -> dict | None:
    """Get prediction for tomorrow using last 8 days from DB."""
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT date, aqi FROM aqi_daily ORDER BY date DESC LIMIT ?", (N_LAGS,)
        ).fetchall()
        conn.close()

        if len(rows) < N_LAGS:
            return None

        lag_values  = [r[1] for r in rows]   # most recent first
        latest_date = rows[0][0]
        pred_date   = (datetime.strptime(latest_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        pred_aqi    = predict_aqi(lag_values)

        return {
            'predicted_aqi':   round(pred_aqi, 1),
            'prediction_date': pred_date,
            'category':        get_aqi_category(pred_aqi),
        }
    except Exception:
        return None


# =============================================================================
# SCHEDULER JOBS
# =============================================================================

def _already_notified(notif_type: str, date: str) -> bool:
    """Check notification_log to prevent duplicate sends on the same day."""
    conn = sqlite3.connect(DB_PATH)
    row  = conn.execute(
        "SELECT id FROM notification_log WHERE type=? AND date=?",
        (notif_type, date)
    ).fetchone()
    conn.close()
    return row is not None


def _log_notification(notif_type: str, date: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO notification_log (type, date, sent_at) VALUES (?, ?, ?)",
        (notif_type, date, now_wib())
    )
    conn.commit()
    conn.close()


def _get_all_subscribers() -> list:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT email FROM subscribers").fetchall()
    conn.close()
    return [r[0] for r in rows]


def job_check_aqi_alert():
    """Run every 30 min: send alert to all subscribers if AQI > 100 (once per day)."""
    print(f"[Scheduler] job_check_aqi_alert — {now_wib()}")
    try:
        aqi_data = fetch_current_aqi_data()
        if not aqi_data:
            print("[Scheduler] AQI alert: failed to fetch data")
            return

        today    = aqi_data['date']
        aqi_val  = aqi_data['aqi']

        if aqi_val <= 100:
            print(f"[Scheduler] AQI alert: AQI={aqi_val} ≤ 100, skip")
            return

        if _already_notified('alert', today):
            print(f"[Scheduler] AQI alert: already sent for {today}, skip")
            return

        emails = _get_all_subscribers()
        if not emails:
            print("[Scheduler] AQI alert: no subscribers")
            return

        pred_data = fetch_prediction_data()
        html = build_email_html(
            aqi_val       = aqi_val,
            category      = aqi_data['category'],
            date_str      = today,
            station       = aqi_data['station'],
            pred_aqi      = pred_data['predicted_aqi']   if pred_data else None,
            pred_date     = pred_data['prediction_date'] if pred_data else None,
            pred_category = pred_data['category']        if pred_data else None,
        )
        cat_label = aqi_data['category']['label_id']
        subject   = f"[PERINGATAN] AQI Jakarta {int(aqi_val)} — {cat_label} ({today})"

        sent = 0
        for addr in emails:
            ok, _ = send_email(addr, subject, html)
            if ok:
                sent += 1

        _log_notification('alert', today)
        print(f"[Scheduler] AQI alert sent to {sent}/{len(emails)} subscribers, AQI={aqi_val}")

    except Exception as e:
        print(f"[Scheduler] AQI alert error: {e}")


def job_daily_notification():
    """Run at 20:00 WIB (or 16:40 for testing): send daily report to all subscribers."""
    print(f"[Scheduler] job_daily_notification — {now_wib()}")
    try:
        today = today_wib()

        if _already_notified('daily', today):
            print(f"[Scheduler] Daily notif: already sent for {today}, skip")
            return

        aqi_data = fetch_current_aqi_data()
        if not aqi_data:
            print("[Scheduler] Daily notif: failed to fetch AQI data")
            return

        emails = _get_all_subscribers()
        if not emails:
            print("[Scheduler] Daily notif: no subscribers")
            return

        pred_data = fetch_prediction_data()
        html = build_email_html(
            aqi_val       = aqi_data['aqi'],
            category      = aqi_data['category'],
            date_str      = aqi_data['date'],
            station       = aqi_data['station'],
            pred_aqi      = pred_data['predicted_aqi']   if pred_data else None,
            pred_date     = pred_data['prediction_date'] if pred_data else None,
            pred_category = pred_data['category']        if pred_data else None,
        )
        subject = f"Laporan Harian AQI Jakarta — {aqi_data['date']} ({aqi_data['category']['label_id']})"

        sent = 0
        for addr in emails:
            ok, _ = send_email(addr, subject, html)
            if ok:
                sent += 1

        _log_notification('daily', today)
        print(f"[Scheduler] Daily notif sent to {sent}/{len(emails)} subscribers")

    except Exception as e:
        print(f"[Scheduler] Daily notif error: {e}")


# ---------------------------------------------------------------------------
# POST /api/subscribe
# Simpan email + kirim welcome email
# ---------------------------------------------------------------------------
@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    data  = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()

    if not email or '@' not in email or '.' not in email.split('@')[-1]:
        return jsonify({'error': 'Email tidak valid'}), 400

    try:
        db = get_db()
        db.execute(
            "INSERT INTO subscribers (email, created_at) VALUES (?, ?)",
            (email, now_wib())
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email sudah terdaftar'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Kirim welcome email dengan AQI hari ini + prediksi besok
    aqi_data  = fetch_current_aqi_data()
    pred_data = fetch_prediction_data()
    email_sent = False
    email_note = ''

    if aqi_data:
        html = build_email_html(
            aqi_val       = aqi_data['aqi'],
            category      = aqi_data['category'],
            date_str      = aqi_data['date'],
            station       = aqi_data['station'],
            is_welcome    = True,
            pred_aqi      = pred_data['predicted_aqi']   if pred_data else None,
            pred_date     = pred_data['prediction_date'] if pred_data else None,
            pred_category = pred_data['category']        if pred_data else None,
        )
        ok, msg = send_email(email, 'Selamat datang di AQI Jakarta!', html)
        email_sent = ok
        email_note = msg

    return jsonify({
        'success':    True,
        'message':    'Email berhasil didaftarkan!',
        'email_sent': email_sent,
        'email_note': email_note if not email_sent else '',
    })


# ---------------------------------------------------------------------------
# POST /api/notify-subscribers
# Kirim AQI hari ini ke semua subscriber
# ---------------------------------------------------------------------------
@app.route('/api/notify-subscribers', methods=['POST'])
def notify_subscribers():
    if not config.EMAIL_ENABLED:
        return jsonify({
            'error': 'Email belum dikonfigurasi.',
            'hint':  'Set EMAIL_ENABLED=True dan isi EMAIL_USER/EMAIL_PASSWORD di config.py'
        }), 503

    aqi_data  = fetch_current_aqi_data()
    if not aqi_data:
        return jsonify({'error': 'Gagal mengambil data AQI dari API'}), 502

    pred_data = fetch_prediction_data()

    db   = get_db()
    rows = db.execute("SELECT email FROM subscribers").fetchall()
    emails = [r['email'] for r in rows]

    if not emails:
        return jsonify({'error': 'Belum ada subscriber terdaftar'}), 404

    html = build_email_html(
        aqi_val       = aqi_data['aqi'],
        category      = aqi_data['category'],
        date_str      = aqi_data['date'],
        station       = aqi_data['station'],
        pred_aqi      = pred_data['predicted_aqi']   if pred_data else None,
        pred_date     = pred_data['prediction_date'] if pred_data else None,
        pred_category = pred_data['category']        if pred_data else None,
    )
    subject = f"Info AQI Jakarta — {aqi_data['date']} ({aqi_data['category']['label_id']})"

    sent = 0
    failed = []
    for addr in emails:
        ok, msg = send_email(addr, subject, html)
        if ok:
            sent += 1
        else:
            failed.append({'email': addr, 'reason': msg})

    return jsonify({
        'success':        True,
        'total':          len(emails),
        'sent':           sent,
        'failed':         len(failed),
        'failed_details': failed,
        'aqi':            aqi_data['aqi'],
        'date':           aqi_data['date'],
    })


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    init_db()

    # -------------------------------------------------------------------------
    # APScheduler — background notification jobs
    # -------------------------------------------------------------------------
    scheduler = BackgroundScheduler(timezone='Asia/Jakarta')

    # Job 1: AQI alert — setiap 30 menit, kirim jika AQI > 100 (1x/hari)
    scheduler.add_job(
        job_check_aqi_alert,
        'interval',
        minutes=30,
        id='aqi_alert',
        replace_existing=True,
    )

    # Job 2: Laporan harian — 20:00 WIB
    scheduler.add_job(
        job_daily_notification,
        CronTrigger(hour=20, minute=0, timezone='Asia/Jakarta'),
        id='daily_notif',
        replace_existing=True,
    )

    scheduler.start()
    print("[OK] Scheduler started — AQI alert every 30 min | Daily report at 20:00 WIB")

    import atexit
    atexit.register(lambda: scheduler.shutdown(wait=False))

    app.run(debug=DEBUG, host='0.0.0.0', port=5000, use_reloader=False)

# Auto-init DB for production environments (like Render)
with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"DB Init error: {e}")
