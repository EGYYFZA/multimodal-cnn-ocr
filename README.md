# HoaxShield - Deteksi Berita Hoaks dengan Multi-Kernel CNN + OCR

> **Status:** research prototype for local use. Model scores below are project-reported and have not been independently reproduced. Do not treat predictions as verified facts.

## Security and validation

The upload endpoint has no authentication or rate limiting. Keep it local until the upload parser dependencies, request-body limits, OCR timeouts, and deployment controls have been reviewed. Limiting reads inside the endpoint does not limit the earlier multipart parsing stage. Never load untrusted pickle/joblib model files.

```sh
node --test tests/evidence-security.test.cjs
python -m pip install -r apps/api/requirements_core.txt httpx==0.28.1
python -m unittest discover -s tests -p 'test_*.py' -v
```

See [SECURITY.md](SECURITY.md).

CI installs the application dependencies, runs `pip check`, exercises the real FastAPI/Jinja/form/upload stack with model, dataset, OCR, and logging services replaced by test doubles, and scans the requirements using `pip-audit`. These checks do not reproduce model accuracy or run OCR. The two deployment manifests use the same updated FastAPI, Jinja, Pillow, and python-multipart pins; successful CI and dependency-audit results are still required before considering deployment.

## 📌 Overview

Sistem deteksi berita hoaks menggunakan Multi-Kernel 1D CNN dengan dukungan OCR untuk ekstraksi teks dari gambar dan video. Model di-training dengan preprocessing yang konsisten untuk akurasi tinggi.

## 🏗️ Struktur Project

```
final_project_skripsi/
├── apps/api/
│   └── app/
│       ├── main.py                    # FastAPI app
│       ├── routes/                    # API endpoints
│       ├── services/                  # Business logic
│       │   ├── model_service.py       # Model inference
│       │   ├── preprocess.py          # Text preprocessing
│       │   ├── ocr_service.py         # OCR extraction
│       │   └── dataset_service.py     # Similarity search
│       ├── static/                    # Frontend assets
│       ├── templates/                 # HTML templates
│       └── assets/                    # Model & data
│           ├── multi_kernel_model.h5  # ✅ Model trained
│           ├── tokenizer.pkl          # ✅ Tokenizer
│           └── datasets/              # Reference datasets
├── retrain_model.py                   # Training script
├── test_prediction.py                 # Testing script
├── start_api.ps1                      # Quick start server
└── README.md                          # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```powershell
# Pastikan virtual environment aktif
.\.venv\Scripts\Activate.ps1

# Install packages (jika belum)
pip install -r apps/requirements.txt
```

### 2. Start Server

```powershell
# Cara termudah - gunakan script
.\start_api.ps1

# Atau manual
cd apps/api
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Access Web Interface

Buka browser: **http://localhost:8000**

## 📊 Model Information

**Model:** Multi-Kernel 1D CNN  
**Validation Accuracy:** 99.29%  
**Threshold:** 0.45 (optimal balance)  
**Max Sequence Length:** 150 tokens  
**Vocabulary Size:** 50,000

### Architecture

- **Parallel CNN kernels:** 2, 3, 4, 5 (128 filters each)
- **GlobalMaxPooling** per kernel
- **Concatenation** → Dropout(0.3) → Dense(128) → Output(sigmoid)

## 🔧 Configuration

### Environment Variables

```powershell
# Model paths (optional - defaults work)
$env:MODEL_PATH = "app/assets/multi_kernel_model.h5"
$env:TOKENIZER_PATH = "app/assets/tokenizer.pkl"

# Threshold (optional - default 0.45)
$env:OPERATING_TAU = "0.45"

# OCR (optional - Tesseract paths)
$env:TESSERACT_EXE = "C:/Program Files/Tesseract-OCR/tesseract.exe"
$env:TESSDATA_PREFIX = "C:/Program Files/Tesseract-OCR/tessdata"

# Dataset for similarity search (optional)
$env:DATASET_FILES = "app/assets/datasets/dataset_gabungan.csv"
```

## 🎯 API Endpoints

### 1. Health Check

```http
GET /api/health
```

Response: Model info, status, configuration

### 2. Predict

```http
POST /api/predict
Content-Type: multipart/form-data

Parameters:
- title: string (optional)
- body: string (optional)
- image_file: file (optional)
- video_file: file (optional)
```

Response:

```json
{
  "label": "HOAKS",
  "prob_hoax": 0.8401,
  "prob_valid": 0.1599,
  "confidence": {
    "level": "TINGGI",
    "margin": 0.3901
  },
  "evidence": [...],
  "used_ocr": false
}
```

### 3. Dataset Stats

```http
GET /api/dataset
```

Response: Dataset status dan jumlah referensi

## 🧪 Testing

### Test Predictions

```powershell
# Set environment untuk test
$env:MODEL_PATH="C:/Users/ACER/OneDrive/Desktop/final_project_skripsi/apps/api/app/assets/multi_kernel_model.h5"
$env:TOKENIZER_PATH="C:/Users/ACER/OneDrive/Desktop/final_project_skripsi/apps/api/app/assets/tokenizer.pkl"

# Run test
python test_prediction.py
```

### Test Preprocessing

```powershell
python test_preprocessing.py
```

## 🔄 Retraining Model

Jika ingin melatih ulang model dengan data baru:

```powershell
python retrain_model.py --data apps/api/app/assets/datasets/dataset_gabungan.csv --epochs 6
```

Script akan:

- ✅ Preprocessing data dengan clean_text yang konsisten
- ✅ Training Multi-Kernel CNN
- ✅ Evaluasi dengan berbagai threshold
- ✅ Simpan model ke `apps/api/app/assets/multi_kernel_model.h5`
- ✅ Simpan tokenizer ke `apps/api/app/assets/tokenizer.pkl`

**Training di Google Colab:** Lihat [TRAINING_COLAB.md](TRAINING_COLAB.md) untuk panduan training dengan GPU gratis.

## 🐛 Troubleshooting

### Model tidak ditemukan

```
FileNotFoundError: Model tidak ditemukan
```

**Solusi:** Jalankan `retrain_model.py` atau pastikan file `multi_kernel_model.h5` ada di `apps/api/app/assets/`

### Tesseract error (OCR)

```
TesseractNotFoundError
```

**Solusi:** Install Tesseract-OCR dan set `TESSDATA_PREFIX`:

```powershell
$env:TESSDATA_PREFIX = "C:/Program Files/Tesseract-OCR/tessdata"
```

### Port already in use

```
ERROR: Address already in use
```

**Solusi:** Ganti port atau kill process yang menggunakan port 8000:

```powershell
# Ganti port
uvicorn app.main:app --reload --port 8001

# Atau kill process
Get-Process | Where-Object {$_.ProcessName -eq "python"} | Stop-Process
```

### Import errors

```
ModuleNotFoundError: No module named 'tensorflow'
```

**Solusi:** Pastikan virtual environment aktif dan install dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r apps/requirements.txt
```

## 📝 Important Notes

### Preprocessing Consistency ⚠️

Model di-training dengan preprocessing yang **SANGAT SPESIFIK**. Jangan ubah urutan atau logika di `preprocess.py`:

1. Hapus tag `[HOAKS]`, `[SALAH]`, dll
2. Lowercase semua teks
3. Hapus URLs
4. Hapus domain tokens (kompas, detik, dll)
5. Hapus label cue words (hoax, palsu, dll)
6. **HANYA simpan huruf a-z dan spasi** (buang angka!)
7. Normalisasi spasi

### Threshold Selection

Model menggunakan sigmoid output. Pilih threshold berdasarkan trade-off:

- **0.35:** Recall tinggi untuk HOAKS (tangkap lebih banyak hoax, false positive lebih tinggi)
- **0.45:** ✅ Balance optimal (recommended)
- **0.50:** Precision tinggi (lebih konservatif, false positive lebih rendah)

## 🔍 Evidence/Similarity Search

Sistem menyediakan fitur "Evidence" untuk menampilkan berita serupa dari dataset referensi (Kompas valid news, TurnBackHoax database). Pada input pendek atau OCR, keputusan hybrid dapat mengganti label CNN berdasarkan evidence. Hasil tetap perlu diverifikasi secara independen.

Dataset referensi:

- `kompas_news.csv` - Berita valid dari Kompas
- `turnbackhoax.csv` - Database hoax verified
- `dataset_gabungan.csv` - Gabungan dataset training

## 📄 License & Credits

**Final Project - Sistem Deteksi Berita Hoaks**  
Model: Multi-Kernel 1D CNN  
Preprocessing: Custom anti-leakage  
OCR: Tesseract + EasyOCR  
Framework: FastAPI + TensorFlow 2.18

---

**Last Updated:** January 28, 2026  
**Status:** Research prototype. The reported 99.29% validation accuracy has not been independently reproduced; deployment security remains under review.
