#!/bin/bash
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
    python3 -m venv venv_consolidador
    source venv_consolidador/bin/activate
fi

# Instalar librerías Python
pip install --upgrade pip
pip install \
    pillow \
    imagededup \
    opencv-python \
    scikit-learn \
    tqdm \
    imagehash

echo "✅ Instalación completada"

# Verificar instalación
echo "🔍 Verificando instalación..."
dcraw -v > /dev/null 2>&1 && echo "✅ dcraw" || echo "❌ dcraw"
convert -version > /dev/null 2>&1 && echo "✅ imagemagick" || echo "❌ imagemagick"
python3 -c "import PIL; print('✅ Pillow')" 2>/dev/null || echo "❌ Pillow"
python3 -c "import imagededup; print('✅ imagededup')" 2>/dev/null || echo "❌ imagededup"
python3 -c "import cv2; print('✅ OpenCV')" 2>/dev/null || echo "❌ OpenCV"

echo "🚀 Sistema listo para usar"