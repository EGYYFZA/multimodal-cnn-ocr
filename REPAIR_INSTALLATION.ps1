# Script untuk memperbaiki instalasi
# Jalankan dengan: .\REPAIR_INSTALLATION.ps1

Write-Host "=== PERBAIKAN INSTALASI DIMULAI ===" -ForegroundColor Green
Write-Host ""

# Cek current directory
$currentDir = Get-Location
Write-Host "Current directory: $currentDir"

# Pastikan di root project
if (-not (Test-Path "apps\api")) {
    Write-Host "Error: Harus dijalankan dari root project folder!" -ForegroundColor Red
    exit 1
}

# Step 1: Bersihkan Python cache
Write-Host "`n[1/7] Membersihkan Python cache..." -ForegroundColor Yellow
Get-ChildItem -Path "apps" -Include __pycache__ -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "  ✓ Python cache dibersihkan" -ForegroundColor Green

# Step 2: Hapus virtual environment lama
Write-Host "`n[2/7] Menghapus virtual environment lama..." -ForegroundColor Yellow
if (Test-Path "apps\api\.venv") {
    Remove-Item -Path "apps\api\.venv" -Recurse -Force -ErrorAction Stop
    Write-Host "  ✓ Virtual environment lama dihapus" -ForegroundColor Green
} else {
    Write-Host "  ℹ Virtual environment tidak ditemukan, skip" -ForegroundColor Cyan
}

# Step 3: Cek disk space
Write-Host "`n[3/7] Mengecek disk space..." -ForegroundColor Yellow
$drive = Get-PSDrive C
$freeGB = [math]::Round($drive.Free / 1GB, 2)
Write-Host "  Drive C free space: $freeGB GB" -ForegroundColor Cyan

if ($freeGB -lt 2) {
    Write-Host "  ⚠ WARNING: Space kurang dari 2GB!" -ForegroundColor Red
    Write-Host "  Rekomendasi: Bersihkan lebih banyak space atau gunakan drive F" -ForegroundColor Yellow
    $continue = Read-Host "  Lanjutkan? (y/n)"
    if ($continue -ne "y") {
        Write-Host "Instalasi dibatalkan" -ForegroundColor Red
        exit 1
    }
}

# Step 4: Buat virtual environment baru di Drive F (lebih banyak space)
Write-Host "`n[4/7] Membuat virtual environment baru di Drive F..." -ForegroundColor Yellow

# Buat folder di Drive F
$venvPath = "F:\python_projects\final_project_venv"
if (-not (Test-Path "F:\python_projects")) {
    New-Item -Path "F:\python_projects" -ItemType Directory -Force | Out-Null
}

# Hapus venv lama di F jika ada
if (Test-Path $venvPath) {
    Write-Host "  Menghapus venv lama di Drive F..." -ForegroundColor Cyan
    Remove-Item -Path $venvPath -Recurse -Force
}

# Buat venv baru
python -m venv $venvPath
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Virtual environment dibuat di: $venvPath" -ForegroundColor Green
} else {
    Write-Host "  ✗ Gagal membuat virtual environment" -ForegroundColor Red
    exit 1
}

# Step 5: Aktifkan virtual environment
Write-Host "`n[5/7] Mengaktifkan virtual environment..." -ForegroundColor Yellow
& "$venvPath\Scripts\Activate.ps1"
Write-Host "  ✓ Virtual environment aktif" -ForegroundColor Green

# Step 6: Upgrade pip
Write-Host "`n[6/7] Mengupgrade pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Pip berhasil diupgrade" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Pip upgrade gagal, tapi lanjutkan..." -ForegroundColor Yellow
}

# Step 7: Install dependencies
Write-Host "`n[7/7] Menginstall dependencies..." -ForegroundColor Yellow
Write-Host "  Ini akan memakan waktu beberapa menit..." -ForegroundColor Cyan

# Set pip cache ke drive F
$env:PIP_CACHE_DIR = "F:\pip_cache"

# Install dari requirements
cd apps\api
pip install --no-cache-dir -r requirements_core.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n  ✓ Semua dependencies berhasil diinstall!" -ForegroundColor Green
} else {
    Write-Host "`n  ⚠ Beberapa package mungkin gagal diinstall" -ForegroundColor Yellow
    Write-Host "  Coba install manual dengan: pip install <package_name>" -ForegroundColor Cyan
}

# Verifikasi instalasi
Write-Host "`n=== VERIFIKASI INSTALASI ===" -ForegroundColor Green
Write-Host "Testing imports..." -ForegroundColor Cyan

$testScript = @"
try:
    import tensorflow as tf
    print(f'  ✓ TensorFlow {tf.__version__}')
except Exception as e:
    print(f'  ✗ TensorFlow: {e}')

try:
    import fastapi
    print('  ✓ FastAPI installed')
except Exception as e:
    print(f'  ✗ FastAPI: {e}')

try:
    import cv2
    print('  ✓ OpenCV installed')
except Exception as e:
    print(f'  ✗ OpenCV: {e}')

try:
    import pytesseract
    print('  ✓ PyTesseract installed')
except Exception as e:
    print(f'  ✗ PyTesseract: {e}')
"@

python -c $testScript

# Informasi akhir
Write-Host "`n=== INSTALASI SELESAI ===" -ForegroundColor Green
Write-Host ""
Write-Host "Virtual environment location: $venvPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Untuk mengaktifkan venv di session baru:" -ForegroundColor Yellow
Write-Host "  $venvPath\Scripts\Activate.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Untuk menjalankan server:" -ForegroundColor Yellow
Write-Host "  cd apps\api" -ForegroundColor White
Write-Host "  $venvPath\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  uvicorn app.main:app --reload --port 8000" -ForegroundColor White
Write-Host ""

# Buat shortcut script untuk menjalankan server
$runScript = @"
# Quick run script
`$venvPath = "$venvPath"
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& "`$venvPath\Scripts\Activate.ps1"

Write-Host "Starting FastAPI server..." -ForegroundColor Green
Set-Location "$(Get-Location)\apps\api"
uvicorn app.main:app --reload --port 8000
"@

Set-Content -Path "RUN_SERVER.ps1" -Value $runScript
Write-Host "Script untuk menjalankan server dibuat: RUN_SERVER.ps1" -ForegroundColor Green
Write-Host "Jalankan dengan: .\RUN_SERVER.ps1" -ForegroundColor Cyan
