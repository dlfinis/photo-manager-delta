#!/bin/bash

# Photo Manager Delta - Installation Script
# Installs system and Python dependencies

set -e  # Exit on any error

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi

echo "Detected OS: $OS"

# Check for virtual environment
if [[ "$1" == "--venv" ]]; then
    echo "Setting up virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    PIP_CMD="python -m pip"
else
    PIP_CMD="pip3"
fi

echo "Installing Python dependencies..."
$PIP_CMD install --upgrade pip
# Instalador de dependencias para el consolidador de fotos

echo "🛠️ Instalando dependencias del sistema..."

# Actualizar repositorios
sudo apt update

# Instalar herramientas del sistema
sudo apt install -y \
    dcraw \
    imagemagick \
    exiv2 \
    exiftool \
    python3-pip \
    python3-venv

echo "📦 Instalando librerías Python..."

# Crear entorno virtual (opcional)
if [ "$1" = "--venv" ]; then
    python3 -m venv venv_consolidator
    source venv_consolidator/bin/activate
fi

# Instalar librerías Python
pip install --upgrade pip
pip install \
    pillow \
    imagededup \
    opencv-python \
    scikit-learn \
    tqdm \
    imagehash \
    pyyaml

echo "✅ Instalación completada"

# Verificar instalación
echo "🔍 Verificando instalación..."
dcraw -v > /dev/null 2>&1 && echo "✅ dcraw" || echo "❌ dcraw"
convert -version > /dev/null 2>&1 && echo "✅ imagemagick" || echo "❌ imagemagick"
python3 -c "import PIL; print('✅ Pillow')" 2>/dev/null || echo "❌ Pillow"
python3 -c "import imagededup; print('✅ imagededup')" 2>/dev/null || echo "❌ imagededup"
python3 -c "import cv2; print('✅ OpenCV')" 2>/dev/null || echo "❌ OpenCV"

echo "🚀 Sistema listo para usar"