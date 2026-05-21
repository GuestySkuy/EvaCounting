#!/bin/bash
# -----------------------------------------------------------------
# Setup script for People Counting System on Raspberry Pi 4
# Run: chmod +x install.sh && ./install.sh
# -----------------------------------------------------------------

set -e # exit immediately if any command fails

echo "=== Starting Raspberry Pi Environment Setup ==="

# Update Package Lists
echo "Updating apt repositories..."
sudo apt update -y

# Install OS Dependencies (Python venv, SQLite)
echo "Installing OS dependencies..."
sudo apt install -y python3-pip python3-venv sqlite3

# Create Project Virtual Environment
echo "Creating python virtual environment..."
python3 -m venv venv

# Activate Virtual Environment and Upgrade Pip
echo "Upgrading pip..."
source venv/bin/activate
pip install --upgrade pip

# Install OpenCV Headless first to prevent GUI dependency installation conflicts
echo "Installing opencv-python-headless..."
pip install opencv-python-headless>=4.8.0

# Install Project Requirements (CPU-only PyTorch and core dependencies)
echo "Installing pip requirements (this may take a few minutes)..."
pip install -r requirements-rpi.txt

# Install Ultralytics WITHOUT heavy unused packages (matplotlib, pandas, seaborn, etc.)
echo "Installing lightweight Ultralytics..."
pip install ultralytics>=8.3.0 --no-deps

# Purge pip cache to save disk space on SD card
echo "Purging pip download cache..."
pip cache purge

# Export Pretrained YOLO Model to NCNN
echo "Downloading and exporting default YOLO model to NCNN format..."
# It will download yolo11n.pt first if not present, then export
python scripts/export_ncnn.py --model yolo11n.pt --imgsz 320

# Run stand-alone benchmark
echo "Running quick benchmark..."
python scripts/benchmark.py

echo "--------------------------------------------------------"
echo "Setup Completed Successfully!"
echo "To test the camera standalone in console:"
echo "  source venv/bin/activate"
echo "  python scripts/test_camera.py --mode count --source 0"
echo "--------------------------------------------------------"
