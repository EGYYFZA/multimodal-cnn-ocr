# Script Simple - Install di Drive C (pastikan ada minimal 3GB space)
# Jalankan dengan: .\REPAIR_SIMPLE.ps1

Write-Host "=== PERBAIKAN SIMPLE (Drive C) ===" -ForegroundColor Green

# Cek space
$drive = Get-PSDrive C
$freeGB = [math]::Round($drive.Free / 1GB, 2)
Write-Host "`nDrive C free space: $freeGB GB" -ForegroundColor Cyan

if ($freeGB -lt 2) {
    Write-Host "ERROR: Space tidak cukup!" -ForegroundColor Red
    Write-Host "Silakan gunakan REPAIR_INSTALLATION.ps1 untuk install di Drive F" -ForegroundColor Yellow
    exit 1
}

# Hapus venv lama
Write-Host "`nMenghapus virtual environment lama..." -ForegroundColor Yellow
Set-Location "apps\api"
if (Test-Path ".venv") {
    Remove-Item -Path ".venv" -Recurse -Force
}

# Buat venv baru
Write-Host "Membuat virtual environment baru..." -ForegroundColor Yellow
python -m venv .venv

# Aktifkan
Write-Host "Mengaktifkan virtual environment..." -ForegroundColor Yellow
& ".\.venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Install dependencies dengan no-cache
Write-Host "Installing dependencies (ini akan lama)..." -ForegroundColor Yellow
Write-Host "Menggunakan --no-cache-dir untuk hemat space..." -ForegroundColor Cyan

pip install --no-cache-dir -r requirements_core.txt

Write-Host "`n=== SELESAI ===" -ForegroundColor Green
Write-Host "Test imports..." -ForegroundColor Cyan

python -c "import tensorflow as tf; print(f'TensorFlow {tf.__version__} OK')"
python -c "import fastapi; print('FastAPI OK')"

Write-Host "`nJalankan server dengan:" -ForegroundColor Yellow
Write-Host "  uvicorn app.main:app --reload --port 8000" -ForegroundColor White
