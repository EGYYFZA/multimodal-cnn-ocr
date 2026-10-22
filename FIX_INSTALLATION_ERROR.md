# Panduan Perbaikan Error Instalasi

## Masalah
- **Error**: `[Errno 28] No space left on device`
- **Penyebab**: Drive C penuh (hanya ~600MB tersisa, butuh minimal 3-5GB)
- **Dampak**: TensorFlow tidak terinstall dengan benar

## Solusi

### Opsi 1: Bersihkan Space Drive C (RECOMMENDED)

#### Langkah 1: Hapus Temporary Files
```powershell
# Jalankan dari terminal PowerShell (Run as Administrator)

# Hapus Windows Temp Files
Remove-Item -Path "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue

# Hapus Pip Cache
pip cache purge

# Hapus Python Cache di project
Get-ChildItem -Path "C:\Users\ACER\OneDrive\Desktop\final_project_skripsi" -Include __pycache__,*.pyc -Recurse -Force | Remove-Item -Recurse -Force

# Cek space lagi
wmic logicaldisk get size,freespace,caption
```

#### Langkah 2: Bersihkan Virtual Environment Lama
```powershell
cd C:\Users\ACER\OneDrive\Desktop\final_project_skripsi

# Hapus .venv di root (jika ada)
if (Test-Path ".venv") { Remove-Item -Path ".venv" -Recurse -Force }

# Hapus .venv di apps/api
cd apps\api
if (Test-Path ".venv") { Remove-Item -Path ".venv" -Recurse -Force }
```

#### Langkah 3: Buat Virtual Environment Baru
```powershell
# Pastikan masih di apps\api
cd C:\Users\ACER\OneDrive\Desktop\final_project_skripsi\apps\api

# Buat virtual environment baru
python -m venv .venv

# Aktifkan
.\.venv\Scripts\Activate.ps1
```

#### Langkah 4: Install Dependencies dengan Cache di Drive F
```powershell
# Set pip cache directory ke drive F yang punya banyak space
$env:PIP_CACHE_DIR = "F:\pip_cache"

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install --no-cache-dir -r requirements_core.txt
```

### Opsi 2: Gunakan Virtual Environment di Drive F

```powershell
# Buat folder untuk project di drive F
New-Item -Path "F:\python_projects\final_project_venv" -ItemType Directory -Force

cd C:\Users\ACER\OneDrive\Desktop\final_project_skripsi\apps\api

# Buat virtual environment di drive F
python -m venv F:\python_projects\final_project_venv

# Aktifkan
F:\python_projects\final_project_venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements_core.txt
```

### Opsi 3: Install dengan No-Cache (Jika Sudah Ada Space)

```powershell
cd C:\Users\ACER\OneDrive\Desktop\final_project_skripsi\apps\api

# Aktifkan venv
.\.venv\Scripts\Activate.ps1

# Install dengan no-cache untuk hemat space
pip install --no-cache-dir tensorflow
pip install --no-cache-dir -r requirements_core.txt
```

## Cara Clean Install (Lengkap)

```powershell
# 1. Hapus semua virtual environments
cd C:\Users\ACER\OneDrive\Desktop\final_project_skripsi
Remove-Item -Path "apps\api\.venv" -Recurse -Force -ErrorAction SilentlyContinue

# 2. Bersihkan pip cache
pip cache purge

# 3. Bersihkan temp Windows (jalankan as Admin)
# Disk Cleanup > Pilih "Temporary files", "Recycle Bin", "Downloads folder"
# Atau jalankan: cleanmgr /sagerun:1

# 4. Cek space
wmic logicaldisk get size,freespace,caption

# 5. Buat venv baru
cd apps\api
python -m venv .venv

# 6. Aktifkan
.\.venv\Scripts\Activate.ps1

# 7. Set cache ke drive F
$env:PIP_CACHE_DIR = "F:\pip_cache"

# 8. Install packages satu per satu (jika masih error)
pip install --no-cache-dir numpy
pip install --no-cache-dir pandas
pip install --no-cache-dir pillow
pip install --no-cache-dir opencv-python
pip install --no-cache-dir pytesseract
pip install --no-cache-dir tensorflow
pip install --no-cache-dir fastapi
pip install --no-cache-dir uvicorn
pip install --no-cache-dir python-multipart
pip install --no-cache-dir scikit-learn
```

## Verifikasi Instalasi

```powershell
# Test import TensorFlow
python -c "import tensorflow as tf; print('TensorFlow version:', tf.__version__)"

# Test import FastAPI
python -c "import fastapi; print('FastAPI installed successfully')"

# Test semua imports
python -c "import tensorflow; import fastapi; import cv2; import pytesseract; print('All packages OK!')"
```

## Jalankan Server

```powershell
cd C:\Users\ACER\OneDrive\Desktop\final_project_skripsi\apps\api

# Aktifkan venv (jika belum)
.\.venv\Scripts\Activate.ps1

# Atau jika venv di drive F:
# F:\python_projects\final_project_venv\Scripts\Activate.ps1

# Jalankan server
uvicorn app.main:app --reload --port 8000
```

## Tips Pencegahan

1. **Selalu monitor disk space**: Minimal 5GB kosong di drive C
2. **Gunakan pip cache di drive lain**:
   ```powershell
   # Tambahkan ke PowerShell profile
   $env:PIP_CACHE_DIR = "F:\pip_cache"
   ```
3. **Bersihkan cache berkala**:
   ```powershell
   pip cache purge
   ```
4. **Gunakan `--no-cache-dir`** untuk instalasi di disk yang terbatas

## Error Yang Sudah Diperbaiki

✅ `[Errno 28] No space left on device` - Dengan bersihkan space
✅ `ModuleNotFoundError: No module named 'tensorflow.python.platform'` - Dengan reinstall TensorFlow
✅ Virtual environment corrupt - Dengan buat ulang venv
