/* =============================================================================
   MAIN.JS — AQI Jakarta Web App
   Vanilla JS: Gauge (Canvas API), Chart.js, i18n, animations, API calls
   ============================================================================= */

'use strict';

/* =============================================================================
   CONSTANTS
   ============================================================================= */

// Skala ISPU resmi Indonesia — 5 kategori
const AQI_CATS = [
  { min:   0, max:  50, labelId: 'Baik',              labelEn: 'Good',           color: '#22c55e', pill: 'pill-good',      textColor: '#14532d' },
  { min:  51, max: 100, labelId: 'Sedang',             labelEn: 'Moderate',       color: '#3b82f6', pill: 'pill-moderate',  textColor: '#fff'    },
  { min: 101, max: 200, labelId: 'Tidak Sehat',        labelEn: 'Unhealthy',      color: '#eab308', pill: 'pill-unhealthy', textColor: '#422006' },
  { min: 201, max: 300, labelId: 'Sangat Tidak Sehat', labelEn: 'Very Unhealthy', color: '#ef4444', pill: 'pill-very',      textColor: '#fff'    },
  { min: 301, max: 999, labelId: 'Berbahaya',          labelEn: 'Hazardous',      color: '#1f2937', pill: 'pill-hazardous', textColor: '#fff'    },
];

const I18N = {
  id: {
    logo_sub:             'Prediksi Harian',
    nav_dashboard:        'Dashboard',
    nav_prediction:       'Prediksi',
    nav_preload:          'Preload Data',
    nav_daily:            'Data Harian',
    nav_about:            'Tentang',
    subscribe_label:      'Notifikasi AQI harian',
    subscribe_placeholder:'Masukkan email',
    subscribe_btn:        'Daftar',
    updated_at:           'Diperbarui:',
    dashboard_aqi_now:    'AQI Jakarta Hari Ini',
    stat_days:            'Hari data tersedia',
    stat_pol:             'Polutan dominan',
    stat_model:           'Model prediksi',
    stat_mae:             'Akurasi model (test)',
    rec_title:            'Rekomendasi Hari Ini',
    rec_waiting:          'Memuat data AQI…',
    dash_pollutants:      'Detail Polutan',
    pred_today:           'AQI Hari Ini',
    pred_tomorrow:        'Prediksi AQI Besok',
    pred_rec_title:       'Rekomendasi untuk Besok',
    pred_empty_title:     'Belum ada data',
    pred_empty_msg:       'Belum ada data. Upload CSV historis dulu ya — minimal 8 hari diperlukan untuk prediksi.',
    pred_go_preload:      'Upload Data Historis',
    pred_chart_title:     'Tren AQI 8 Hari Terakhir',
    legend_history:       'Historis',
    legend_pred:          'Prediksi',
    pred_divider:         'Atau prediksi dari stasiun lain',
    csv_upload_title:     'Prediksi dari CSV',
    csv_upload_sub:       'Upload CSV dengan kolom <code>date</code> + <code>AQI</code> (minimal 8 baris)',
    drop_zone_text:       'Drag & drop CSV di sini, atau klik untuk pilih',
    disclaimer_title:     'Disclaimer',
    disclaimer_1:         'Model dilatih pada data stasiun DKI 2 Kebon Jeruk, Jakarta Barat.',
    disclaimer_2:         'Data real-time diambil dari stasiun KBN Marunda, Jakarta Utara — mungkin berbeda dari stasiun latih.',
    disclaimer_3:         'AQI dihitung berdasarkan PM2.5 sebagai polutan dominan.',
    disclaimer_4:         'Akurasi prediksi dapat bervariasi tergantung kondisi cuaca dan aktivitas industri.',
    disclaimer_5:         'Gunakan prediksi ini sebagai panduan, bukan keputusan medis.',
    preload_title:        'Upload Data Historis',
    preload_sub:          'Upload CSV untuk mengisi database. Dibutuhkan minimal 8 hari data agar prediksi otomatis bisa dijalankan.',
    preload_format:       'Format CSV yang diterima:',
    preload_format_note:  'Nama kolom alternatif: <code>tanggal</code>, <code>datetime</code> / <code>ispu</code>, <code>pm25</code>',
    preload_inserted:     'Data baru',
    preload_skipped:      'Dilewati',
    preload_total:        'Total baris',
    preload_tip_title:    'Tips Penggunaan',
    preload_tip_1:        'Upload minimal 8 hari data untuk mengaktifkan prediksi otomatis.',
    preload_tip_2:        'Data duplikat (tanggal sama) otomatis dilewati, tidak akan ada data ganda.',
    preload_tip_3:        'Setelah preload berhasil, buka halaman Prediksi untuk melihat hasil.',
    preload_tip_4:        'Data real-time dari API AQICN otomatis ditambahkan setiap kali halaman dibuka.',
    daily_title:          'Data AQI Harian',
    daily_count_label:    'data',
    col_date:             'Tanggal',
    col_aqi:              'AQI',
    col_category:         'Kategori',
    col_source:           'Sumber',
    col_station:          'Stasiun',
    daily_empty_title:    'Belum ada data',
    daily_empty_msg:      'Belum ada data. Upload CSV historis dulu ya',
    about_model_title:    'Tentang Model',
    about_model_sub:      'T-8 Lag Features · Scikit-learn',
    about_mae:            'MAE (Test)',
    about_cc:             'Korelasi (CC)',
    about_train_data:     'Data Latih',
    about_test_data:      'Data Uji',
    about_station:        'Stasiun Latih',
    about_pipeline_title: 'Pipeline Model',
    pipeline_a_title:     'Pengumpulan Data',
    pipeline_a_desc:      'Data AQI harian dari AQICN & KLHK, stasiun DKI 2 Kebon Jeruk',
    pipeline_b_title:     'Preprocessing',
    pipeline_b_desc:      'Imputasi nilai hilang, normalisasi, pembentukan fitur lag T-1 hingga T-8',
    pipeline_c_title:     'Feature Selection',
    pipeline_c_desc:      'Seleksi fitur lag optimal menggunakan korelasi dan importance RF',
    pipeline_cp_title:    'Hyperparameter Tuning',
    pipeline_cp_desc:     'Optuna bayesian optimization, 100 trials per model',
    pipeline_e_title:     'Evaluasi & Deployment',
    pipeline_e_desc:      'Model terbaik dievaluasi pada data test 2025, lalu di-deploy sebagai web app',
    about_ref_title:      'Referensi',
    about_disclaimer_title:'Disclaimer',
    notify_btn:           'Kirim Notifikasi AQI',
    stat_section_model:   'Performa Model & Status Sistem',
    col_pollutant:        'Polutan',
    col_unit:             'Satuan',
  },
  en: {
    logo_sub:             'Daily Forecast',
    nav_dashboard:        'Dashboard',
    nav_prediction:       'Prediction',
    nav_preload:          'Preload Data',
    nav_daily:            'Daily Data',
    nav_about:            'About',
    subscribe_label:      'Daily AQI Notifications',
    subscribe_placeholder:'Enter your email',
    subscribe_btn:        'Subscribe',
    updated_at:           'Updated:',
    dashboard_aqi_now:    'Jakarta AQI Today',
    stat_days:            'Days of data available',
    stat_pol:             'Dominant pollutant',
    stat_model:           'Prediction model',
    stat_mae:             'Model accuracy (test)',
    rec_title:            "Today's Recommendation",
    rec_waiting:          'Loading AQI data…',
    dash_pollutants:      'Pollutant Details',
    pred_today:           "Today's AQI",
    pred_tomorrow:        "Tomorrow's AQI Prediction",
    pred_rec_title:       'Recommendation for Tomorrow',
    pred_empty_title:     'No data yet',
    pred_empty_msg:       'No data yet. Please upload historical CSV first — minimum 8 days required for prediction.',
    pred_go_preload:      'Upload Historical Data',
    pred_chart_title:     'Last 8 Days AQI Trend',
    legend_history:       'Historical',
    legend_pred:          'Prediction',
    pred_divider:         'Or predict from another station',
    csv_upload_title:     'Predict from CSV',
    csv_upload_sub:       'Upload CSV with <code>date</code> + <code>AQI</code> columns (minimum 8 rows)',
    drop_zone_text:       'Drag & drop CSV here, or click to select',
    disclaimer_title:     'Disclaimer',
    disclaimer_1:         'Model was trained on data from DKI 2 Kebon Jeruk station, West Jakarta.',
    disclaimer_2:         'Real-time data is fetched from KBN Marunda station, North Jakarta — may differ from training station.',
    disclaimer_3:         'AQI is calculated based on PM2.5 as the dominant pollutant.',
    disclaimer_4:         'Prediction accuracy may vary depending on weather conditions and industrial activity.',
    disclaimer_5:         'Use this prediction as a guide, not medical advice.',
    preload_title:        'Upload Historical Data',
    preload_sub:          'Upload CSV to populate the database. At least 8 days of data are required to enable automatic prediction.',
    preload_format:       'Accepted CSV format:',
    preload_format_note:  'Alternative column names: <code>tanggal</code>, <code>datetime</code> / <code>ispu</code>, <code>pm25</code>',
    preload_inserted:     'New records',
    preload_skipped:      'Skipped',
    preload_total:        'Total rows',
    preload_tip_title:    'Usage Tips',
    preload_tip_1:        'Upload at least 8 days of data to enable automatic prediction.',
    preload_tip_2:        'Duplicate records (same date) are automatically skipped — no duplicates will be created.',
    preload_tip_3:        'After a successful preload, go to the Prediction page to view results.',
    preload_tip_4:        'Real-time data from the AQICN API is automatically added each time a page is opened.',
    daily_title:          'Daily AQI Data',
    daily_count_label:    'records',
    col_date:             'Date',
    col_aqi:              'AQI',
    col_category:         'Category',
    col_source:           'Source',
    col_station:          'Station',
    daily_empty_title:    'No data yet',
    daily_empty_msg:      'No data yet. Please upload historical CSV first.',
    about_model_title:    'About the Model',
    about_model_sub:      'T-8 Lag Features · Scikit-learn',
    about_mae:            'MAE (Test)',
    about_cc:             'Correlation (CC)',
    about_train_data:     'Training Data',
    about_test_data:      'Test Data',
    about_station:        'Training Station',
    about_pipeline_title: 'Model Pipeline',
    pipeline_a_title:     'Data Collection',
    pipeline_a_desc:      'Daily AQI data from AQICN & KLHK, DKI 2 Kebon Jeruk station',
    pipeline_b_title:     'Preprocessing',
    pipeline_b_desc:      'Missing value imputation, normalization, lag feature engineering T-1 to T-8',
    pipeline_c_title:     'Feature Selection',
    pipeline_c_desc:      'Optimal lag feature selection using correlation and RF importance',
    pipeline_cp_title:    'Hyperparameter Tuning',
    pipeline_cp_desc:     'Optuna Bayesian optimization, 100 trials per model',
    pipeline_e_title:     'Evaluation & Deployment',
    pipeline_e_desc:      'Best model evaluated on 2025 test data, then deployed as a web app',
    about_ref_title:      'References',
    about_disclaimer_title:'Disclaimer',
    notify_btn:           'Send AQI Notification',
    stat_section_model:   'Model Performance & System Status',
    col_pollutant:        'Pollutant',
    col_unit:             'Unit',
  },
};

/* =============================================================================
   STATE
   ============================================================================= */
let currentLang    = 'id';
let currentPage    = 'dashboard';
let csvChart       = null;
let gaugeAnims     = {};   // canvasId → rAF handle

/* =============================================================================
   HELPERS
   ============================================================================= */

function getCategory(aqi) {
  const v = parseFloat(aqi) || 0;
  return AQI_CATS.find(c => v >= c.min && v <= c.max) || AQI_CATS[AQI_CATS.length - 1];
}

function t(key) {
  return I18N[currentLang][key] || I18N['id'][key] || key;
}

function formatDateDisplay(dateStr) {
  // "2026-04-09" → "9 Apr 2026"
  try {
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString(currentLang === 'id' ? 'id-ID' : 'en-GB', {
      day: 'numeric', month: 'short', year: 'numeric'
    });
  } catch { return dateStr; }
}

function formatTimestamp(isoStr) {
  // "2026-04-08 17:00:00" → "8 Apr 2026, 17:00 WIB"
  try {
    const d = new Date(isoStr.replace(' ', 'T') + '+07:00');
    const day   = d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
    const hhmm  = d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
    return `${day}, ${hhmm} WIB`;
  } catch { return isoStr; }
}

function setTimestamp(str) {
  const el = document.getElementById('globalTimestamp');
  if (el) el.textContent = str;
}

/* Easing: approximation of cubic-bezier(0.22, 1, 0.36, 1) */
function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3);
}
/* Easing: ease-out quartic for count-up */
function easeOutQuart(t) {
  return 1 - Math.pow(1 - t, 4);
}

function showEl(id)  { const e = document.getElementById(id); if (e) e.style.display = ''; }
function hideEl(id)  { const e = document.getElementById(id); if (e) e.style.display = 'none'; }
function blockEl(id) { const e = document.getElementById(id); if (e) e.style.display = 'block'; }

function setPill(elId, aqi) {
  const el = document.getElementById(elId);
  if (!el) return;
  const cat = getCategory(aqi);
  el.textContent  = currentLang === 'en' ? cat.labelEn : cat.labelId;
  el.className    = 'aqi-pill ' + cat.pill;
}

function sourceLabel(src) {
  const map = { aqicn_api: 'API', csv_upload: 'CSV', preload: 'Preload' };
  const cls  = { aqicn_api: 'api', csv_upload: 'csv', preload: 'preload' };
  return `<span class="source-badge ${cls[src] || ''}">${map[src] || src}</span>`;
}

/* =============================================================================
   LANGUAGE TOGGLE
   ============================================================================= */

function setLang(lang) {
  currentLang = lang;
  document.getElementById('btnID').classList.toggle('active', lang === 'id');
  document.getElementById('btnEN').classList.toggle('active', lang === 'en');
  applyLang();
}

function applyLang() {
  // Text content
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    const val = I18N[currentLang][key];
    if (val !== undefined) el.innerHTML = val;
  });
  // Placeholders
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.dataset.i18nPlaceholder;
    const val = I18N[currentLang][key];
    if (val !== undefined) el.placeholder = val;
  });
  // Update breadcrumb
  const bc = document.getElementById('pageBreadcrumb');
  if (bc) bc.textContent = t('nav_' + currentPage);
  // Refresh pills if data already loaded
  refreshVisiblePills();
  // Re-render daily table so category labels update
  if (currentPage === 'daily') {
    const tbody = document.getElementById('dailyTableBody');
    if (tbody && tbody.children.length > 0) loadDailyData();
  }
}

function refreshVisiblePills() {
  // Re-label any visible pills from current AQI values
  const pairs = [
    ['aqiTodayNumber',  'aqiTodayPill'],
    ['dashTomorrowNum', 'dashTomorrowPill'],
    ['csvAqiNum',       'csvAqiPill'],
  ];
  pairs.forEach(([numId, pillId]) => {
    const el = document.getElementById(numId);
    if (el && el.textContent !== '—') {
      const aqi = parseFloat(el.textContent);
      if (!isNaN(aqi)) setPill(pillId, aqi);
    }
  });
}

/* =============================================================================
   NAVIGATION
   ============================================================================= */

function navigateTo(page) {
  currentPage = page;

  // Update nav active state
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });

  // Update breadcrumb
  const bc = document.getElementById('pageBreadcrumb');
  if (bc) bc.textContent = t('nav_' + page);

  // Show / hide pages
  document.querySelectorAll('.page').forEach(el => el.classList.remove('active'));
  const target = document.getElementById('page-' + page);
  if (target) target.classList.add('active');

  // Close mobile sidebar
  closeSidebar();

  // Page-specific init
  if (page === 'dashboard') loadDashboard();
  if (page === 'prediction') loadPrediction();
  if (page === 'daily')      loadDailyData();
}

function initNavigation() {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', e => {
      e.preventDefault();
      navigateTo(el.dataset.page);
    });
  });
}

/* =============================================================================
   GAUGE — Canvas API
   ============================================================================= */

const GAUGE_START  = (3 / 4) * Math.PI;   // 135° (7:30 o'clock)
const GAUGE_SWEEP  = (3 / 2) * Math.PI;   // 270°
const GAUGE_MAX    = 300;                  // AQI 300+ = full gauge

function drawGaugeFrame(ctx, cx, cy, radius, lw, aqi, progress) {
  const cat = getCategory(aqi);
  const fraction = Math.min(parseFloat(aqi) || 0, GAUGE_MAX) / GAUGE_MAX;

  // Background track
  ctx.beginPath();
  ctx.arc(cx, cy, radius, GAUGE_START, GAUGE_START + GAUGE_SWEEP);
  ctx.strokeStyle = '#e2e8f0';
  ctx.lineWidth = lw;
  ctx.lineCap = 'round';
  ctx.stroke();

  // Colored progress arc
  const endAngle = GAUGE_START + GAUGE_SWEEP * fraction * progress;
  if (fraction > 0) {
    ctx.beginPath();
    ctx.arc(cx, cy, radius, GAUGE_START, endAngle);
    ctx.strokeStyle = cat.color;
    ctx.lineWidth = lw;
    ctx.lineCap = 'round';
    ctx.stroke();
  }
}

function animateGauge(canvasId, aqi) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx    = canvas.getContext('2d');
  const W      = canvas.width;
  const H      = canvas.height;
  const cx     = W / 2;
  const cy     = H / 2 + Math.round(H * 0.05);
  const radius = Math.round(W * 0.36);
  const lw     = Math.round(W * 0.058);

  // Cancel any running animation for this canvas
  if (gaugeAnims[canvasId]) cancelAnimationFrame(gaugeAnims[canvasId]);

  const duration  = 1500;
  const startTime = performance.now();

  function frame(now) {
    const elapsed = now - startTime;
    const rawT    = Math.min(elapsed / duration, 1);
    const eased   = easeOutCubic(rawT);

    ctx.clearRect(0, 0, W, H);
    drawGaugeFrame(ctx, cx, cy, radius, lw, aqi, eased);

    if (rawT < 1) {
      gaugeAnims[canvasId] = requestAnimationFrame(frame);
    } else {
      delete gaugeAnims[canvasId];
    }
  }

  gaugeAnims[canvasId] = requestAnimationFrame(frame);
}

function renderGaugeStatic(canvasId, aqi) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  if (gaugeAnims[canvasId]) cancelAnimationFrame(gaugeAnims[canvasId]);
  const ctx    = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  drawGaugeFrame(ctx, W/2, H/2 + Math.round(H*0.05), Math.round(W*0.36), Math.round(W*0.058), aqi, 1);
}

/* =============================================================================
   COUNT-UP ANIMATION
   ============================================================================= */

function countUp(elId, target, duration = 1400) {
  const el = document.getElementById(elId);
  if (!el) return;
  const startTime = performance.now();
  const startVal  = parseFloat(el.textContent) || 0;

  function frame(now) {
    const t    = Math.min((now - startTime) / duration, 1);
    const val  = startVal + (target - startVal) * easeOutQuart(t);
    el.textContent = Math.round(val);
    if (t < 1) requestAnimationFrame(frame);
    else el.textContent = Math.round(target);
  }
  requestAnimationFrame(frame);
}

/* =============================================================================
   DASHBOARD (hari ini + prediksi besok + chart + polutan)
   ============================================================================= */

function loadDashboard() {
  hideEl('dashEmptyState');
  hideEl('dashChartCard');
  hideEl('dashPredRec');
  fetchDashboardData();
  updateDailyCount();
}

async function fetchDashboardData() {
  showEl('dashboardSpinner');
  showEl('dashPredSpinner');

  // 1. AQI hari ini
  let todayData = null;
  try {
    const res  = await fetch('/api/current-aqi');
    const data = await res.json();
    if (!data.error) {
      todayData = data;
      hideEl('dashboardSpinner');
      renderDashboardToday(data);
    }
  } catch (err) {
    hideEl('dashboardSpinner');
    renderDashboardError(err.message);
  }

  // 2. Prediksi besok
  try {
    const res  = await fetch('/api/predict-auto', { method: 'POST' });
    const data = await res.json();
    hideEl('dashPredSpinner');

    if (res.status === 422 || data.error) {
      showEl('dashEmptyState');
      return;
    }

    renderDashboardTomorrow(data);

  } catch (err) {
    hideEl('dashPredSpinner');
    showEl('dashEmptyState');
  }
}

function renderDashboardToday(data) {
  const aqi = data.aqi;
  const cat = getCategory(aqi);

  animateGauge('gaugeToday', aqi);
  countUp('aqiTodayNumber', aqi);
  setPill('aqiTodayPill', aqi);

  const recBar  = document.getElementById('dashRecBar');
  const recText = document.getElementById('dashRecText');
  if (recBar)  recBar.style.background = cat.color;
  if (recText) recText.textContent = currentLang === 'en'
    ? data.category.recommendation_en
    : data.category.recommendation_id;

  if (data.updated_at) setTimestamp(formatTimestamp(data.updated_at));

  // Polutan indexed table
  const iaqi = data.iaqi;
  if (iaqi && Object.keys(iaqi).length > 0) {
    const tbody = document.getElementById('pollutantBody');
    if (tbody) {
      tbody.innerHTML = Object.entries(iaqi).map(([k, v], i) => {
        return `<tr>
          <td class="pt-index">${i + 1}</td>
          <td class="pt-name">${k.toUpperCase()}</td>
          <td class="pt-value">${v}</td>
        </tr>`;
      }).join('');
      showEl('dashPollCard');
    }
  }
}

function renderDashboardTomorrow(data) {
  const predAqi = data.predicted_aqi;
  const cat     = getCategory(predAqi);

  animateGauge('gaugeDashTomorrow', predAqi);
  countUp('dashTomorrowNum', predAqi);
  setPill('dashTomorrowPill', predAqi);

  const dateEl = document.getElementById('dashTomorrowDate');
  if (dateEl) dateEl.textContent = formatDateDisplay(data.prediction_date);

  const recBar  = document.getElementById('dashPredRecBar');
  const recText = document.getElementById('dashPredRecText');
  if (recBar)  recBar.style.background = cat.color;
  if (recText) recText.textContent = currentLang === 'en'
    ? data.category.recommendation_en
    : data.category.recommendation_id;
  showEl('dashPredRec');

  // Tren chart
  renderDashChart(data.history, data.prediction_date, predAqi);
  showEl('dashChartCard');
  updateChartLegend(data.history, predAqi);
}

function renderDashboardError(msg) {
  const recText = document.getElementById('dashRecText');
  if (recText) recText.textContent = currentLang === 'id'
    ? `Gagal memuat data AQI. Periksa token API di config.py.`
    : `Failed to load AQI data. Check API token in config.py.`;
  const numEl = document.getElementById('aqiTodayNumber');
  if (numEl) numEl.textContent = '—';
  renderGaugeStatic('gaugeToday', 0);
}

async function updateDailyCount() {
  try {
    const res  = await fetch('/api/daily-data');
    const data = await res.json();
    const el   = document.getElementById('statDaysAvail');
    if (el && data.count !== undefined) el.textContent = data.count;
  } catch {}
}

/* =============================================================================
   PREDICTION PAGE — CSV only (auto-prediction sudah di dashboard)
   ============================================================================= */

function loadPrediction() {
  hideEl('predEmptyState');
  hideEl('predCsvResult');
}

/* =============================================================================
   PREDICTION — CSV UPLOAD
   ============================================================================= */

function initPredCsvUpload() {
  const dropZone = document.getElementById('predDropZone');
  const fileInput = document.getElementById('predCsvInput');
  if (!dropZone || !fileInput) return;

  dropZone.addEventListener('click', () => fileInput.click());

  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) uploadPredCsv(file);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) uploadPredCsv(fileInput.files[0]);
    fileInput.value = '';
  });
}

async function uploadPredCsv(file) {
  const msgEl = document.getElementById('predCsvMsg');
  setMsg(msgEl, 'info', currentLang === 'id' ? `Memproses ${file.name}…` : `Processing ${file.name}…`);
  hideEl('predCsvResult');

  const form = new FormData();
  form.append('file', file);

  try {
    const res  = await fetch('/api/predict-csv', { method: 'POST', body: form });
    const data = await res.json();

    if (data.error) {
      setMsg(msgEl, 'error', data.error);
      return;
    }

    setMsg(msgEl, 'success',
      currentLang === 'id'
        ? `Prediksi berhasil dari ${data.filename}`
        : `Prediction successful from ${data.filename}`);

    renderCsvPrediction(data);

  } catch (err) {
    setMsg(msgEl, 'error', err.message);
  }
}

function renderCsvPrediction(data) {
  const predAqi = data.predicted_aqi;
  const cat     = getCategory(predAqi);

  showEl('predCsvResult');

  // Gauge
  animateGauge('gaugeCsv', predAqi);

  const numEl = document.getElementById('csvAqiNum');
  if (numEl) countUp('csvAqiNum', predAqi);

  setPill('csvAqiPill', predAqi);

  const dateEl = document.getElementById('csvPredDate');
  if (dateEl) dateEl.textContent = formatDateDisplay(data.prediction_date);

  // Recommendation
  const recBar  = document.getElementById('csvRecBar');
  const recText = document.getElementById('csvRecText');
  if (recBar)  recBar.style.background = cat.color;
  if (recText) recText.textContent = currentLang === 'en'
    ? data.category.recommendation_en
    : data.category.recommendation_id;

  // Chart
  renderCsvChart(data.history, data.prediction_date, predAqi);
}

/* =============================================================================
   CHART.JS HELPERS
   ============================================================================= */

function buildChartConfig(history, predDate, predAqi) {
  const labels   = history.map(r => r.date);
  const histVals = history.map(r => r.aqi);
  const predCat  = getCategory(predAqi);

  // All labels: 8 historical + 1 prediction
  const allLabels = [...labels, predDate];

  // Single bar dataset: historical solid, prediction semi-transparent
  const allVals = [...histVals, predAqi];

  const bgColors = allLabels.map((_, i) => {
    if (i < histVals.length) {
      // historical — solid
      return getCategory(histVals[i]).color + 'cc';
    }
    // prediction — semi-transparent
    return predCat.color + '66';
  });

  const borderColors = allLabels.map((_, i) => {
    if (i < histVals.length) return getCategory(histVals[i]).color;
    return predCat.color;
  });

  const borderWidths = allLabels.map((_, i) => i < histVals.length ? 1 : 2);

  return {
    type: 'bar',
    data: {
      labels: allLabels,
      datasets: [
        {
          label: currentLang === 'id' ? 'AQI' : 'AQI',
          data: allVals,
          backgroundColor: bgColors,
          borderColor: borderColors,
          borderWidth: borderWidths,
          borderRadius: 3,
          borderDash: allLabels.map((_, i) => i < histVals.length ? [] : [4, 3]),
          animation: {
            delay: ctx => ctx.dataIndex * 70,
          },
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const isLast = ctx.dataIndex === allLabels.length - 1;
              const prefix = isLast
                ? (currentLang === 'id' ? ' Prediksi' : ' Forecast')
                : ' AQI';
              return `${prefix}: ${ctx.raw}`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 },
            color: '#94a3b8',
            maxRotation: 45,
          },
        },
        y: {
          beginAtZero: true,
          grid: { color: '#f1f3f8' },
          ticks: {
            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 },
            color: '#94a3b8',
          },
        },
      },
      animation: {
        duration: 800,
        easing: 'easeOutQuart',
      },
    },
  };
}

function updateChartLegend(history, predAqi) {
  // Pick a representative color for the solid legend bar:
  // use the most recent historical bar's category color
  const lastHist = history.length ? history[history.length - 1].aqi : predAqi;
  const solidColor = getCategory(lastHist).color;
  const predColor  = getCategory(predAqi).color;

  const solid = document.querySelector('.legend-bar--solid');
  const faded = document.querySelector('.legend-bar--faded');
  if (solid) solid.style.background = solidColor + 'cc';
  if (faded) {
    faded.style.background   = predColor + '40';
    faded.style.borderColor  = predColor;
  }
}

let dashChartInstance = null;

function renderDashChart(history, predDate, predAqi) {
  const canvas = document.getElementById('dashChart');
  if (!canvas) return;
  if (dashChartInstance) { dashChartInstance.destroy(); dashChartInstance = null; }
  dashChartInstance = new Chart(canvas, buildChartConfig(history, predDate, predAqi));
}

function renderCsvChart(history, predDate, predAqi) {
  const canvas = document.getElementById('csvChart');
  if (!canvas) return;
  if (csvChart) { csvChart.destroy(); csvChart = null; }
  csvChart = new Chart(canvas, buildChartConfig(history, predDate, predAqi));
}

/* =============================================================================
   DAILY DATA
   ============================================================================= */

async function loadDailyData() {
  hideEl('dailyTableWrap');
  hideEl('dailyEmpty');
  showEl('dailySpinner');

  try {
    const res  = await fetch('/api/daily-data');
    const data = await res.json();
    hideEl('dailySpinner');

    const count = document.getElementById('dailyCount');
    if (count) count.textContent = data.count || 0;

    if (!data.data || data.data.length === 0) {
      showEl('dailyEmpty');
      return;
    }

    renderDailyTable(data.data);
    showEl('dailyTableWrap');

  } catch (err) {
    hideEl('dailySpinner');
    showEl('dailyEmpty');
    console.error('loadDailyData:', err);
  }
}

function renderDailyTable(records) {
  const tbody = document.getElementById('dailyTableBody');
  if (!tbody) return;

  tbody.innerHTML = records.map(r => {
    const cat = getCategory(r.aqi);
    const label = currentLang === 'en' ? cat.labelEn : cat.labelId;
    return `<tr>
      <td>${formatDateDisplay(r.date)}</td>
      <td><strong style="color:${cat.color}">${r.aqi}</strong></td>
      <td><span class="aqi-pill ${cat.pill}" style="font-size:.68rem">${label}</span></td>
      <td>${sourceLabel(r.source)}</td>
      <td style="color:#94a3b8;font-size:.78rem">${r.station || '—'}</td>
    </tr>`;
  }).join('');
}

/* =============================================================================
   PRELOAD CSV
   ============================================================================= */

function initPreloadCsvUpload() {
  const dropZone  = document.getElementById('preloadDropZone');
  const fileInput = document.getElementById('preloadCsvInput');
  if (!dropZone || !fileInput) return;

  dropZone.addEventListener('click', () => fileInput.click());

  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) uploadPreloadCsv(file);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) uploadPreloadCsv(fileInput.files[0]);
    fileInput.value = '';
  });
}

async function uploadPreloadCsv(file) {
  const msgEl = document.getElementById('preloadMsg');
  hideEl('preloadResult');
  setMsg(msgEl, 'info', currentLang === 'id' ? `Mengunggah ${file.name}…` : `Uploading ${file.name}…`);

  const form = new FormData();
  form.append('file', file);

  try {
    const res  = await fetch('/api/preload-csv', { method: 'POST', body: form });
    const data = await res.json();

    if (data.error) {
      setMsg(msgEl, 'error', data.error);
      return;
    }

    setMsg(msgEl, 'success', data.message);

    document.getElementById('preloadInserted').textContent = data.inserted;
    document.getElementById('preloadSkipped').textContent  = data.skipped;
    document.getElementById('preloadTotal').textContent    = data.total;
    document.getElementById('preloadResultMsg').textContent = data.message;
    showEl('preloadResult');

    // Reset daily count
    updateDailyCount();

  } catch (err) {
    setMsg(msgEl, 'error', err.message);
  }
}

/* =============================================================================
   SUBSCRIBE
   ============================================================================= */

function initSubscribe() {
  const form = document.getElementById('subscribeForm');
  if (!form) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const emailEl = document.getElementById('subscribeEmail');
    const msgEl   = document.getElementById('subscribeMsg');
    const email   = emailEl.value.trim();

    if (!email) return;

    const btn = form.querySelector('.subscribe-btn');
    btn.disabled = true;

    try {
      const res  = await fetch('/api/subscribe', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ email }),
      });
      const data = await res.json();

      if (data.error) {
        msgEl.textContent = data.error;
        msgEl.className   = 'subscribe-msg error';
      } else {
        msgEl.textContent = currentLang === 'id' ? '✓ Email terdaftar!' : '✓ Subscribed!';
        msgEl.className   = 'subscribe-msg success';
        emailEl.value     = '';
        setTimeout(() => { msgEl.textContent = ''; }, 4000);
      }
    } catch (err) {
      msgEl.textContent = err.message;
      msgEl.className   = 'subscribe-msg error';
    } finally {
      btn.disabled = false;
    }
  });
}

/* =============================================================================
   MOBILE HAMBURGER
   ============================================================================= */

function initHamburger() {
  const btn     = document.getElementById('hamburger');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  if (!btn || !sidebar || !overlay) return;

  btn.addEventListener('click', () => {
    const open = sidebar.classList.toggle('open');
    btn.classList.toggle('open', open);
    overlay.classList.toggle('open', open);
  });

  overlay.addEventListener('click', closeSidebar);
}

function closeSidebar() {
  document.getElementById('sidebar')?.classList.remove('open');
  document.getElementById('hamburger')?.classList.remove('open');
  document.getElementById('sidebarOverlay')?.classList.remove('open');
}

/* =============================================================================
   UTILITY
   ============================================================================= */

function setMsg(el, type, text) {
  if (!el) return;
  el.innerHTML   = text;
  el.className   = 'upload-msg ' + type;
}

/* =============================================================================
   NOTIFY SUBSCRIBERS
   ============================================================================= */

async function sendNotification() {
  const btn    = document.getElementById('notifyBtn');
  const msgEl  = document.getElementById('notifyMsg');
  if (!btn || !msgEl) return;

  btn.disabled     = true;
  msgEl.className  = 'notify-msg';
  msgEl.textContent = currentLang === 'id' ? 'Mengirim…' : 'Sending…';

  try {
    const res  = await fetch('/api/notify-subscribers', { method: 'POST' });
    const data = await res.json();

    if (data.error) {
      msgEl.className  = 'notify-msg error';
      msgEl.textContent = data.hint || data.error;
    } else {
      msgEl.className  = 'notify-msg success';
      msgEl.textContent = currentLang === 'id'
        ? `Terkirim ke ${data.sent} dari ${data.total} subscriber`
        : `Sent to ${data.sent} of ${data.total} subscriber(s)`;
    }
  } catch (err) {
    msgEl.className  = 'notify-msg error';
    msgEl.textContent = err.message;
  } finally {
    btn.disabled = false;
    setTimeout(() => { msgEl.textContent = ''; }, 6000);
  }
}

/* =============================================================================
   TIMESTAMP — auto refresh every minute
   ============================================================================= */

function initTimestamp() {
  function tick() {
    const now = new Date();
    const day = now.toLocaleDateString('id-ID', {
      timeZone: 'Asia/Jakarta',
      day: 'numeric', month: 'short', year: 'numeric'
    });
    const hhmm = now.toLocaleTimeString('id-ID', {
      timeZone: 'Asia/Jakarta',
      hour: '2-digit', minute: '2-digit'
    });
    setTimestamp(`${day}, ${hhmm} WIB`);
  }
  tick();
  setInterval(tick, 60000);
}

/* =============================================================================
   INIT
   ============================================================================= */

function init() {
  initTimestamp();
  applyLang();
  initNavigation();
  initSubscribe();
  initPredCsvUpload();
  initPreloadCsvUpload();
  initHamburger();
  navigateTo('dashboard');
}

document.addEventListener('DOMContentLoaded', init);
