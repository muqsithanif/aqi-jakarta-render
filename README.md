# aqi-jakarta-render

Daily Air Quality Index (AQI / ISPU) forecasting and real-time monitoring web application for Jakarta, powered by an autoregressive Random Forest model tuned with Optuna.

## Overview

Air pollution in metropolitan Jakarta (PM2.5 / PM10) exhibits strong autoregressive patterns and meteorological dependencies. This project serves a pre-trained machine learning model to forecast day-ahead air quality, fetch live telemetry from the World Air Quality Index (AQICN) Marunda station, and issue automated health alerts based on Indonesia's official 5-tier ISPU (Indeks Standar Pencemar Udara) standard.

## Features

- **Next-Day AQI Prediction:** Autoregressive Random Forest model utilizing 8-day historical lag values ($t-1$ to $t-8$).
- **Live Station Ingestion:** Real-time AQI telemetry streaming from AQICN monitoring stations.
- **ISPU Health Advisory:** Automated classification into Indonesia's 5 official categories:
  - *Baik (0-50)*
  - *Sedang (51-100)*
  - *Tidak Sehat (101-200)*
  - *Sangat Tidak Sehat (201-300)*
  - *Berbahaya (301+)*
- **Automated Alerts:** Email notification dispatch via Gmail SMTP for vulnerable demographic groups.
- **Interactive UI:** Responsive dashboard displaying historical charts, prediction curves, and safety guidelines.

## Project Structure

```
aqi-jakarta-render/
├── deploy_pythonanywhere/
│   ├── app.py                     # Flask application & REST endpoints
│   ├── config.py                  # Environment-driven configuration
│   ├── init_db.py                 # SQLite database initialization
│   ├── pkl/
│   │   └── fitted_rf.pkl          # Pre-trained tuned Random Forest model
│   ├── static/                    # Dashboard CSS and JavaScript assets
│   ├── templates/                 # HTML templates
│   └── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Quick Start

### 1. Installation

```bash
git clone https://github.com/muqsithanif/aqi-jakarta-render.git
cd aqi-jakarta-render

python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r deploy_pythonanywhere/requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and fill in your optional API token:

```bash
cp .env.example .env
```

### 3. Run Application

```bash
python deploy_pythonanywhere/init_db.py
python deploy_pythonanywhere/app.py
```
Open your browser at `http://127.0.0.1:5000`.
