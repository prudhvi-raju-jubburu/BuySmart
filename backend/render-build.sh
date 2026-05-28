#!/usr/bin/env bash
set -o errexit

# If run from repository root, move into backend directory
if [ -d "backend" ]; then
  cd backend
fi

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create local bin directory
LOCAL_BIN_DIR="bin"
mkdir -p "$LOCAL_BIN_DIR"

if [[ ! -d "$LOCAL_BIN_DIR/chrome" ]]; then
  echo "Installing Chrome for Testing and ChromeDriver locally..."
  
  # Download Chrome
  CHROME_URL="https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/120.0.6099.109/linux64/chrome-linux64.zip"
  wget -q -O /tmp/chrome.zip "$CHROME_URL"
  unzip -q /tmp/chrome.zip -d /tmp
  mv /tmp/chrome-linux64 "$LOCAL_BIN_DIR/chrome"
  rm /tmp/chrome.zip

  # Download ChromeDriver
  CHROMEDRIVER_URL="https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/120.0.6099.109/linux64/chromedriver-linux64.zip"
  wget -q -O /tmp/chromedriver.zip "$CHROMEDRIVER_URL"
  unzip -q /tmp/chromedriver.zip -d /tmp
  mv /tmp/chromedriver-linux64/chromedriver "$LOCAL_BIN_DIR/chromedriver"
  rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64

  chmod +x "$LOCAL_BIN_DIR/chrome/chrome"
  chmod +x "$LOCAL_BIN_DIR/chromedriver"
  
  echo "Local Chrome and ChromeDriver successfully installed in $LOCAL_BIN_DIR"
else
  echo "Using cached local Chrome and ChromeDriver"
fi

# Verify version diagnostics
./bin/chrome/chrome --version
./bin/chromedriver --version
