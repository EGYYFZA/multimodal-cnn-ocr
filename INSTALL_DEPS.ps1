# Activate venv dan install dependencies
$venvPath = "F:\python_projects\final_project_venv"

Write-Host "`n=== INSTALLING DEPENDENCIES ===" -ForegroundColor Green
Write-Host "This may take 5-10 minutes..." -ForegroundColor Yellow
Write-Host ""

# Aktifkan venv
& "$venvPath\Scripts\Activate.ps1"

# Set pip cache ke F
$env:PIP_CACHE_DIR = "F:\pip_cache"

# Upgrade pip
Write-Host "[1/3] Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip --quiet

# Install dependencies
Write-Host "[2/3] Installing dependencies from requirements_core.txt..." -ForegroundColor Cyan
Set-Location "apps\api"
pip install --no-cache-dir -r requirements_core.txt

# Verify
Write-Host "[3/3] Verifying installation..." -ForegroundColor Cyan
python -c "import tensorflow as tf; print(f'✓ TensorFlow {tf.__version__}')"
python -c "import fastapi; print('✓ FastAPI')"
python -c "import cv2; print('✓ OpenCV')"
python -c "import pytesseract; print('✓ PyTesseract')"

Write-Host "`n=== INSTALLATION COMPLETE ===" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the virtual environment:" -ForegroundColor Yellow
Write-Host "  $venvPath\Scripts\Activate.ps1" -ForegroundColor White
Write-Host ""
Write-Host "To run the server:" -ForegroundColor Yellow
Write-Host "  cd apps\api" -ForegroundColor White
Write-Host "  uvicorn app.main:app --reload --port 8000" -ForegroundColor White
