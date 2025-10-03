"""
Utilidades del Sistema
=====================

Funciones auxiliares y configuración.
"""

import logging
import subprocess
import sys
from pathlib import Path

def configurar_logging(nivel=logging.INFO):
    """Configura el sistema de logging"""
    logging.basicConfig(
        level=nivel,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('consolidacion.log', encoding='utf-8')
        ]
    )

def validar_dependencias():
    """Valida que las dependencias estén instaladas"""
    logger = logging.getLogger(__name__)
    
    # Verificar dcraw
    try:
        subprocess.run(["dcraw", "-v"], capture_output=True, check=True)
        logger.debug("✅ dcraw disponible")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("⚠️ dcraw no disponible - archivos RAW no se procesarán")
    
    # Verificar ImageMagick
    try:
        subprocess.run(["convert", "-version"], capture_output=True, check=True)
        logger.debug("✅ ImageMagick disponible")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("⚠️ ImageMagick no disponible")
    
    # Verificar librerías Python
    try:
        import PIL
        logger.debug("✅ Pillow disponible")
    except ImportError:
        logger.error("❌ Pillow no disponible - instalar con: pip install pillow")
        sys.exit(1)
    
    try:
        import imagededup
        logger.debug("✅ imagededup disponible")
    except ImportError:
        logger.warning("⚠️ imagededup no disponible - detección visual limitada")
    
    try:
        import cv2
        logger.debug("✅ OpenCV disponible")
    except ImportError:
        logger.warning("⚠️ OpenCV no disponible - detección avanzada limitada")

def mostrar_ayuda_instalacion():
    """Muestra ayuda para instalar dependencias"""
    print("""
🛠️ INSTALACIÓN DE DEPENDENCIAS

Sistema (Ubuntu/Debian):
    sudo apt update
    sudo apt install -y dcraw imagemagick exiv2 python3-pip

Python:
    pip install pillow imagededup opencv-python scikit-learn tqdm

Verificación:
    dcraw -v
    convert -version
    python -c "import PIL, imagededup, cv2; print('✅ Todo instalado')"
    """)