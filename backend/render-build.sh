#!/usr/bin/env bash
set -o errexit

apt-get update

apt-get install -y \
    wget \
    gnupg \
    unzip \
    chromium \
    chromium-driver

which chromium
which chromedriver

chromium --version
chromedriver --version

pip install --upgrade pip
pip install -r requirements.txt
