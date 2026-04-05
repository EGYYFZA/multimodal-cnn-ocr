# ✅ CHECKLIST: Verifikasi Sistem Deteksi Hoax

**Tanggal:** 28 Januari 2026  
**Status:** Ready for Testing

---

## 🎯 TUJUAN

Memastikan sistem deteksi hoax memberikan hasil yang **AKURAT** sesuai dengan:

1. ✅ Dataset training (dataset_gabungan.csv)
2. ✅ Preprocessing konsisten antara training dan inference
3. ✅ Threshold optimal (0.40 - sudah divalidasi)
4. ✅ Model parameter (MAX_LEN=150, sigmoid output)

---

## 📋 CHECKLIST VERIFIKASI

### ✅ 1. Preprocessing Konsisten

**File:** `apps/api/app/services/preprocess.py`

```python
def clean_text(text: str, source_hint: Optional[str] = None) -> str:
    # ✅ Hapus tag [HOAKS], [SALAH]
    # ✅ Lowercase
    # ✅ Hapus URL
    # ✅ Hapus DOMAIN_TOKENS (turnbackhoax, kompas, detik)
    # ✅ Hapus URL_TOKENS (http, www, com, id)
    # ✅ Hapus LABEL_CUES (hoax, penipuan, palsu, fitnah)
    # ✅ HANYA a-z dan spasi (BUANG ANGKA!)
    # ✅ Rapikan spasi
```

**Test Command:**

```bash
cd c:\Users\ACER\OneDrive\Desktop\final_project_skripsi
python test_preprocessing.py
```

**Expected Output:**

```
✅ PASS - Semua token yang harus dihapus sudah bersih
✅ Preprocessing KONSISTEN dengan training!
```

---

### ✅ 2. Model Configuration

**File:** `apps/api/app/services/model_service.py`

| Parameter     | Value        | Status                  |
| ------------- | ------------ | ----------------------- |
| MAX_LEN       | 150          | ✅ Sama dengan training |
| Output Mode   | sigmoid1     | ✅ Detected otomatis    |
| Threshold     | 0.40         | ✅ Divalidasi           |
| Preprocessing | clean_text() | ✅ Konsisten            |

---

### ✅ 3. Threshold Configuration

**File:** `apps/api/app/services/config.py`

```python
operating_tau: float = 0.40  # ✅ Validated threshold
```

**Penjelasan:**

- **< 0.40** → Label: VALID
- **≥ 0.40** → Label: HOAKS

**Mengapa 0.40?**

- 0.25 (sebelumnya) → Terlalu sensitif, banyak False Positive
- 0.40 (sekarang) → Balance optimal antara precision & recall
- 0.50 (terlalu tinggi) → Miss banyak hoax (False Negative)

---

### ✅ 4. Model & Tokenizer Files

**Required Files:**

```
final_project_skripsi/
└── apps/
    └── api/
        └── app/
            └── assets/
                ├── mkcnn_model.keras  ✅ (dari project_skripsi)
                └── tokenizer.pkl      ✅ (dari project_skripsi)
```

**Cara Copy:**

```bash
# Dari PowerShell
Copy-Item "c:\Users\ACER\OneDrive\Desktop\project_skripsi\mkcnn_model.keras" `
          "c:\Users\ACER\OneDrive\Desktop\final_project_skripsi\apps\api\app\assets\"

Copy-Item "c:\Users\ACER\OneDrive\Desktop\project_skripsi\tokenizer.pkl" `
          "c:\Users\ACER\OneDrive\Desktop\final_project_skripsi\apps\api\app\assets\"
```

---

## 🧪 TESTING WORKFLOW

### Step 1: Test Preprocessing

```bash
python test_preprocessing.py
```

**Expected:**

- ✅ Tidak ada angka
- ✅ Tidak ada tag []
- ✅ Tidak ada kata label cues
- ✅ Tidak ada domain/URL tokens
- ✅ Hanya a-z dan spasi

### Step 2: Test Prediction

```bash
python test_prediction.py
```

**Expected:**

- ✅ Accuracy ≥ 80%
- ✅ Berita VALID terdeteksi sebagai VALID
- ✅ Berita HOAKS terdeteksi sebagai HOAKS

### Step 3: Test API

```bash
cd apps\api
python -m uvicorn app.main:app --reload
```

**Test dengan curl/Postman:**

**Test 1 - Berita VALID:**

```bash
POST http://localhost:8000/predict
Content-Type: multipart/form-data

title: Presiden Resmikan Tol Baru
body: Presiden Jokowi meresmikan jalan tol Balikpapan-Samarinda pada Senin pagi. Tol sepanjang 99 kilometer ini diharapkan dapat memperlancar distribusi logistik.
```

**Expected Response:**

```json
{
  "label": "VALID",
  "prob_hoax": 0.25,
  "prob_valid": 0.75,
  "threshold_used": 0.4,
  "confidence": {
    "level": "TINGGI",
    "margin": 0.15
  }
}
```

**Test 2 - Berita HOAKS:**

```bash
POST http://localhost:8000/predict
Content-Type: multipart/form-data

title: Pemerintah Bagikan Uang Gratis
body: BREAKING NEWS! Pemerintah akan membagikan uang tunai Rp10 juta kepada setiap warga Indonesia. Segera daftar sebelum terlambat!
```

**Expected Response:**

```json
{
  "label": "HOAKS",
  "prob_hoax": 0.82,
  "prob_valid": 0.18,
  "threshold_used": 0.4,
  "confidence": {
    "level": "TINGGI",
    "margin": 0.42
  }
}
```

---

## 🔍 TROUBLESHOOTING

### ❌ Masalah: "Model tidak ditemukan"

**Solusi:**

```bash
# Copy model dari project_skripsi
Copy-Item "c:\Users\ACER\OneDrive\Desktop\project_skripsi\mkcnn_model.keras" `
          "c:\Users\ACER\OneDrive\Desktop\final_project_skripsi\apps\api\app\assets\"
```

### ❌ Masalah: "Tokenizer tidak ditemukan"

**Solusi:**

```bash
# Copy tokenizer dari project_skripsi
Copy-Item "c:\Users\ACER\OneDrive\Desktop\project_skripsi\tokenizer.pkl" `
          "c:\Users\ACER\OneDrive\Desktop\final_project_skripsi\apps\api\app\assets\"
```

### ❌ Masalah: Berita VALID terdeteksi sebagai HOAKS (False Positive)

**Penyebab:**

- Threshold terlalu rendah

**Solusi:**

```python
# Naikkan threshold di config.py
operating_tau: float = 0.45  # Dari 0.40 → 0.45
```

### ❌ Masalah: Berita HOAKS terdeteksi sebagai VALID (False Negative)

**Penyebab:**

- Threshold terlalu tinggi
- Hoax terlalu halus/sophisticated

**Solusi:**

```python
# Turunkan sedikit threshold di config.py
operating_tau: float = 0.35  # Dari 0.40 → 0.35
```

### ❌ Masalah: Accuracy < 60%

**Penyebab:**

- Preprocessing tidak konsisten
- Model yang digunakan bukan hasil training terakhir

**Solusi:**

1. Jalankan `python test_preprocessing.py` untuk verifikasi
2. Pastikan menggunakan model & tokenizer terbaru
3. Cek apakah `clean_text()` di preprocess.py sama dengan train_mkcnn.py
4. Pertimbangkan re-training model

---

## 📊 INTERPRETASI HASIL

### Confidence Level

| Level  | Margin      | Arti                                          |
| ------ | ----------- | --------------------------------------------- |
| TINGGI | ≥ 0.25      | Model sangat yakin (prob jauh dari threshold) |
| SEDANG | 0.15 - 0.25 | Model cukup yakin                             |
| RENDAH | < 0.15      | Model ragu-ragu (prob dekat threshold)        |

### Probability Score

| Prob HOAKS  | Label | Rekomendasi                                    |
| ----------- | ----- | ---------------------------------------------- |
| 0.00 - 0.30 | VALID | Berita sangat kredibel                         |
| 0.30 - 0.40 | VALID | Berita cukup kredibel, perlu verifikasi ringan |
| 0.40 - 0.60 | HOAKS | Berita mencurigakan, perlu fact-check          |
| 0.60 - 0.80 | HOAKS | Berita sangat mencurigakan                     |
| 0.80 - 1.00 | HOAKS | Hampir pasti hoax                              |

---

## 🎓 BEST PRACTICES

### ✅ DO:

1. ✅ Selalu test preprocessing konsistency sebelum deployment
2. ✅ Monitor accuracy secara berkala dengan real data
3. ✅ Kumpulkan feedback user untuk improvement
4. ✅ Dokumentasikan setiap perubahan threshold
5. ✅ Backup model & tokenizer sebelum update

### ❌ DON'T:

1. ❌ Ubah preprocessing tanpa re-training model
2. ❌ Ubah threshold tanpa validasi
3. ❌ Deploy tanpa testing
4. ❌ Ignore False Positive/Negative pattern
5. ❌ Hardcode threshold tanpa reasoning

---

## 📈 MONITORING & MAINTENANCE

### Metrics to Track:

1. **Accuracy** - Overall correctness
2. **Precision** - False Positive rate (VALID → HOAKS salah)
3. **Recall** - False Negative rate (HOAKS → VALID salah)
4. **F1-Score** - Balance precision & recall
5. **Confidence Distribution** - Berapa banyak prediksi dengan confidence tinggi

### When to Re-train:

- Accuracy turun < 70%
- Banyak False Positive/Negative dari user feedback
- Ada dataset baru yang signifikan
- Pattern hoax berubah (new tactics)

---

## ✅ FINAL CHECKLIST

**Sebelum Go Live:**

- [ ] Model & tokenizer file sudah ada di `app/assets/`
- [ ] Test preprocessing: `python test_preprocessing.py` → ✅ PASS
- [ ] Test prediction: `python test_prediction.py` → Accuracy ≥ 80%
- [ ] Test API dengan berita VALID → Label: VALID
- [ ] Test API dengan berita HOAKS → Label: HOAKS
- [ ] Test OCR (jika ada gambar dengan teks)
- [ ] Threshold sudah optimal (0.40 atau hasil tuning)
- [ ] Dokumentasi lengkap untuk maintenance
- [ ] Backup model & config sebelum deployment

**Jika semua ✅ → READY FOR PRODUCTION!**

---

**Created by:** GitHub Copilot  
**Last Updated:** 28 Januari 2026  
**Version:** 2.0
