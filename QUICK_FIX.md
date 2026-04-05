# 🚀 QUICK FIX GUIDE

## Masalah
- ❌ `[Errno 28] No space left on device`
- ❌ `ModuleNotFoundError: No module named 'tensorflow.python.platform'`
- ❌ TensorFlow corrupt/tidak lengkap

## Solusi Cepat

### Opsi 1: Install di Drive F (RECOMMENDED) ⭐
Drive F punya **269GB** space kosong, Drive C hanya **0.57GB**

```powershell
# Jalankan script otomatis
.\REPAIR_INSTALLATION.ps1
```

**Kelebihan:**
- ✅ Tidak perlu khawatir space
- ✅ Instalasi lengkap semua packages
- ✅ Otomatis membuat run script

**Setelah selesai:**
```powershell
# Cara 1: Gunakan shortcut
.\RUN_SERVER.ps1

# Cara 2: Manual
F:\python_projects\final_project_venv\Scripts\Activate.ps1
cd apps\api
uvicorn app.main:app --reload --port 8000
```

---

### Opsi 2: Install di Drive C (Perlu bersihkan space dulu)

#### Langkah 1: Bersihkan Space
```powershell
# Hapus temp files (Run as Admin)
Remove-Item -Path "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue

# Atau gunakan Disk Cleanup
cleanmgr

# Cek space (minimal 3GB)
wmic logicaldisk get size,freespace,caption
```

#### Langkah 2: Jalankan Repair Simple
```powershell
.\REPAIR_SIMPLE.ps1
```

---

### Opsi 3: Manual Installation (Jika script gagal)

```powershell
# 1. Hapus venv lama
cd apps\api
Remove-Item -Path ".venv" -Recurse -Force

# 2. Buat venv di Drive F
python -m venv F:\final_project_venv

# 3. Aktifkan
F:\final_project_venv\Scripts\Activate.ps1

# 4. Set cache ke F
$env:PIP_CACHE_DIR = "F:\pip_cache"

# 5. Install packages
pip install --no-cache-dir tensorflow
pip install --no-cache-dir fastapi uvicorn
pip install --no-cache-dir opencv-python pytesseract
pip install --no-cache-dir pandas numpy scikit-learn nltk
pip install --no-cache-dir python-multipart

# 6. Test
python -c "import tensorflow; print('OK')"

# 7. Run server
cd apps\api
uvicorn app.main:app --reload --port 8000
```

---

## Verifikasi

```powershell
# Test semua imports
python -c "import tensorflow, fastapi, cv2, pytesseract; print('✓ All OK!')"

# Cek TensorFlow version
python -c "import tensorflow as tf; print(tf.__version__)"
```

---

## Files Yang Dibuat

- 📄 `FIX_INSTALLATION_ERROR.md` - Penjelasan lengkap masalah dan solusi
- 🔧 `REPAIR_INSTALLATION.ps1` - Script otomatis (RECOMMENDED, install di Drive F)
- 🔧 `REPAIR_SIMPLE.ps1` - Script simple (install di Drive C)
- 🚀 `RUN_SERVER.ps1` - Auto-generated script untuk run server (setelah repair)
- 📋 `QUICK_FIX.md` - File ini

---

## Troubleshooting

### 1. Script tidak bisa dijalankan (Execution Policy)
```powershell
# Set execution policy (Run as Admin)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Atau bypass untuk satu script
powershell -ExecutionPolicy Bypass -File .\REPAIR_INSTALLATION.ps1
```

### 2. Python command not found
```powershell
# Cek Python installed
python --version

# Atau gunakan py launcher
py -m venv .venv
py -m pip install -r requirements_core.txt
```

### 3. Masih error "No space left"
```powershell
# Cek space detail
Get-PSDrive C | Format-List

# Bersihkan lebih agresif
pip cache purge
Remove-Item -Path "$env:TEMP\*" -Recurse -Force
Remove-Item -Path "$env:LOCALAPPDATA\pip\cache" -Recurse -Force

# Gunakan Disk Cleanup untuk bersihkan Windows files
cleanmgr /sagerun:1
```

### 4. TensorFlow masih error setelah install
```powershell
# Uninstall semua TensorFlow
pip uninstall tensorflow tensorflow-intel -y

# Install ulang specific version
pip install --no-cache-dir tensorflow==2.15.0

# Atau gunakan versi CPU only (lebih kecil)
pip install --no-cache-dir tensorflow-cpu
```

---

## Rekomendasi

**Gunakan Opsi 1 (Install di Drive F)** karena:
- ✅ Drive F punya 269GB space
- ✅ Tidak perlu repot bersihkan Drive C
- ✅ Lebih aman dan stabil
- ✅ Script otomatis handle semuanya

**Jalankan:**
```powershell
.\REPAIR_INSTALLATION.ps1
```

Lalu jalankan server dengan:
```powershell
.\RUN_SERVER.ps1
```

---

## Need Help?

Jika masih ada error, check:
1. [FIX_INSTALLATION_ERROR.md](FIX_INSTALLATION_ERROR.md) - Penjelasan detail
2. Error logs di terminal
3. Python version: `python --version` (harus 3.9+)
4. Pip version: `pip --version`
