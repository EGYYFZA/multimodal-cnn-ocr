# ============================================================
# Start API Server dengan Environment Variables yang Benar
# ============================================================

Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host "="*79
Write-Host " STARTING HOAXSHIELD API SERVER" -ForegroundColor Yellow
Write-Host "="*80 -ForegroundColor Cyan

# Get project root (folder script ini berada)
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = $SCRIPT_DIR

# Set environment variables dengan absolute paths
$env:MODEL_PATH = "$PROJECT_ROOT/apps/api/app/assets/multi_kernel_model.h5"
$env:TOKENIZER_PATH = "$PROJECT_ROOT/apps/api/app/assets/tokenizer.pkl"
$env:TESSDATA_PREFIX = "C:/Program Files/Tesseract-OCR/tessdata"

Write-Host "`n[INFO] Environment Configuration:" -ForegroundColor Green
Write-Host "  MODEL_PATH     = $env:MODEL_PATH" -ForegroundColor Gray
Write-Host "  TOKENIZER_PATH = $env:TOKENIZER_PATH" -ForegroundColor Gray
Write-Host "  TESSDATA_PREFIX = $env:TESSDATA_PREFIX" -ForegroundColor Gray

# Check if model exists
if (-not (Test-Path $env:MODEL_PATH)) {
    Write-Host "`n[ERROR] Model file not found!" -ForegroundColor Red
    Write-Host "  Expected at: $env:MODEL_PATH" -ForegroundColor Yellow
    Write-Host "`n  Run training first:" -ForegroundColor Yellow
    Write-Host "  python retrain_model.py --data apps/api/app/assets/datasets/dataset_gabungan.csv" -ForegroundColor Gray
    exit 1
}

Write-Host "`n[✓] Model file found" -ForegroundColor Green

# Change to API directory
Set-Location "$PROJECT_ROOT/apps/api"

Write-Host "`n[INFO] Starting Uvicorn server..." -ForegroundColor Cyan
Write-Host "  Server will be available at: " -NoNewline
Write-Host "http://localhost:8000" -ForegroundColor Yellow
Write-Host ""

# Start server dengan path relatif dari .venv yang benar
& "$PROJECT_ROOT/.venv/Scripts/python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
